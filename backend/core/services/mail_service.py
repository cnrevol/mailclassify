import logging
from datetime import datetime, timedelta
from typing import List, Optional
import requests
from django.utils import timezone
from ..models import CCUserMailInfo, CCEmail

logger = logging.getLogger(__name__)

class OutlookMailService:
    """
    Outlook邮件服务类
    使用Microsoft Graph API处理邮件
    """
    GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'
    AUTH_BASE = 'https://login.microsoftonline.com'
    SCOPE = 'https://graph.microsoft.com/Mail.Read'

    def __init__(self, user_mail: CCUserMailInfo):
        self.user_mail = user_mail
        self._access_token = None

    def _get_access_token(self) -> str:
        """获取访问令牌"""
        # 如果已有有效的访问令牌，直接返回
        if (self.user_mail.access_token and self.user_mail.token_expires and
                self.user_mail.token_expires > timezone.now()):
            logger.debug("使用现有的访问令牌")
            return self.user_mail.access_token

        # 如果有刷新令牌，使用刷新令牌获取新的访问令牌
        if self.user_mail.refresh_token:
            logger.debug("使用刷新令牌获取新的访问令牌")
            return self._refresh_access_token()
        
        # 没有刷新令牌，无法自动获取访问令牌
        logger.error("没有刷新令牌，无法自动获取访问令牌")
        raise ValueError("需要用户授权。请先完成 OAuth 授权流程获取刷新令牌。")

    def _refresh_access_token(self) -> str:
        """使用刷新令牌获取新的访问令牌"""
        token_url = f"{self.AUTH_BASE}/{self.user_mail.tenant_id}/oauth2/v2.0/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.user_mail.client_id,
            'client_secret': self.user_mail.client_secret,
            'refresh_token': self.user_mail.refresh_token,
            'scope': self.SCOPE
        }

        try:
            logger.debug(f"刷新访问令牌: {token_url}")
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            # 更新令牌信息
            self.user_mail.access_token = token_data['access_token']
            self.user_mail.token_expires = timezone.now() + timedelta(seconds=token_data['expires_in'])
            
            # 如果响应中包含新的刷新令牌，也更新它
            if 'refresh_token' in token_data:
                self.user_mail.refresh_token = token_data['refresh_token']
                self.user_mail.save(update_fields=['access_token', 'token_expires', 'refresh_token'])
            else:
                self.user_mail.save(update_fields=['access_token', 'token_expires'])

            logger.debug("成功刷新访问令牌")
            return self.user_mail.access_token
        except Exception as e:
            logger.error(f"刷新访问令牌失败: {str(e)}")
            raise

    def _get_headers(self) -> dict:
        """获取API请求头"""
        return {
            'Authorization': f'Bearer {self._get_access_token()}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def fetch_emails(self, limit: Optional[int] = None, hours: Optional[int] = None, skip_processed: bool = True) -> List[CCEmail]:
        """
        获取收件箱邮件列表
        
        Args:
            limit: 获取的邮件数量
            hours: 获取指定小时数内的邮件
            skip_processed: 是否跳过已处理的邮件
        """
        try:
            # 构建查询参数
            params = {
                '$select': 'id,subject,sender,receivedDateTime,body,categories,importance,hasAttachments',
                '$orderby': 'receivedDateTime desc',
                '$top': min(limit, 50) if limit else 50
            }

            # 如果指定了时间范围，添加过滤条件
            if hours:
                # 使用 UTC 时间，并格式化为 ISO 8601 格式
                time_threshold = (timezone.now() - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')
                params['$filter'] = f"receivedDateTime ge {time_threshold}"
                
            # 获取邮件列表 - 修改为只获取收件箱邮件
            headers = self._get_headers()
            
            # 首先获取收件箱文件夹ID
            inbox_response = requests.get(
                f"{self.GRAPH_API_BASE}/me/mailFolders/inbox",
                headers=headers
            )
            
            if inbox_response.status_code != 200:
                logger.error(f"获取收件箱信息失败: {inbox_response.status_code} {inbox_response.text}")
                return []
                
            inbox_data = inbox_response.json()
            inbox_id = inbox_data.get('id')
            
            if not inbox_id:
                logger.error("无法获取收件箱ID")
                return []
                
            # 使用收件箱ID获取邮件
            response = requests.get(
                f"{self.GRAPH_API_BASE}/me/mailFolders/{inbox_id}/messages",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"获取邮件失败: {response.status_code} {response.text}")
                return []
                
            data = response.json()
            messages = data.get('value', [])
            logger.info(f"从收件箱获取了 {len(messages)} 封邮件")
            
            # 处理邮件数据
            emails = []
            processed_count = 0
            
            for msg in messages:
                message_id = msg.get('id')
                
                # 检查邮件是否已存在于数据库中
                existing_email = CCEmail.objects.filter(message_id=message_id).first()
                
                if existing_email:
                    # 如果邮件已存在且已处理，且需要跳过已处理邮件，则跳过
                    if skip_processed and existing_email.is_processed:
                        processed_count += 1
                        continue
                    
                    # 如果邮件已存在但未处理，或不需要跳过已处理邮件，则使用现有记录
                    emails.append(existing_email)
                    continue
                
                # 处理新邮件
                subject = msg.get('subject', '(无主题)')
                sender_info = msg.get('sender', {}).get('emailAddress', {})
                sender = sender_info.get('address', '')
                received_time = msg.get('receivedDateTime')
                
                # 转换时间格式
                if received_time:
                    received_time = datetime.fromisoformat(received_time.replace('Z', '+00:00'))
                else:
                    received_time = timezone.now()
                
                # 获取邮件正文
                body = msg.get('body', {})
                content_type = body.get('contentType', 'text')
                content = body.get('content', '')
                
                # 获取邮件重要性
                importance = msg.get('importance', 'normal')
                
                # 获取附件信息
                has_attachments = msg.get('hasAttachments', False)
                
                # 创建邮件记录
                email = CCEmail(
                    user_mail=self.user_mail,
                    message_id=message_id,
                    subject=subject,
                    sender=sender,
                    received_time=received_time,
                    content=content,
                    importance=importance,
                    has_attachments=has_attachments
                )
                
                # 保存邮件记录
                email.save()
                
                # 如果有附件，获取附件信息
                if has_attachments:
                    self._fetch_attachments(email, message_id)
                
                emails.append(email)
            
            if processed_count > 0:
                logger.info(f"跳过了 {processed_count} 封已处理的邮件")
                
            return emails
            
        except Exception as e:
            logger.error(f"获取邮件失败: {str(e)}", exc_info=True)
            return []

    def _mark_as_read(self, message_id: str) -> None:
        """将邮件标记为已读"""
        try:
            url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}"
            data = {
                "isRead": True
            }
            response = requests.patch(url, headers=self._get_headers(), json=data)
            response.raise_for_status()
            logger.debug(f"邮件 {message_id} 已标记为已读")
        except Exception as e:
            logger.error(f"标记邮件为已读失败: {str(e)}")
            
    def _fetch_attachments(self, email: CCEmail, message_id: str) -> None:
        """
        获取邮件附件信息
        
        Args:
            email: 邮件对象
            message_id: 邮件ID
        """
        try:
            # 获取附件列表
            url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}/attachments"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"获取附件失败: {response.status_code} {response.text}")
                return
                
            data = response.json()
            attachments = data.get('value', [])
            
            if not attachments:
                logger.debug(f"邮件 {message_id} 没有附件")
                return
                
            # 处理附件信息
            attachment_count = len(attachments)
            total_size = 0
            attachments_info = []
            
            for attachment in attachments:
                attachment_id = attachment.get('id')
                name = attachment.get('name', '未命名附件')
                content_type = attachment.get('contentType', 'application/octet-stream')
                size = attachment.get('size', 0)
                
                total_size += size
                
                attachments_info.append({
                    'id': attachment_id,
                    'name': name,
                    'content_type': content_type,
                    'size': size
                })
            
            # 更新邮件附件信息
            email.attachment_count = attachment_count
            email.total_attachment_size = total_size
            email.attachments_info = attachments_info
            email.save(update_fields=['attachment_count', 'total_attachment_size', 'attachments_info'])
            
            logger.debug(f"邮件 {message_id} 的附件信息已更新，共 {attachment_count} 个附件")
            
        except Exception as e:
            logger.error(f"获取附件信息失败: {str(e)}", exc_info=True) 