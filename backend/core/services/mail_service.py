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

    def fetch_emails(self, limit: Optional[int] = None, hours: Optional[int] = None) -> List[CCEmail]:
        """
        获取邮件列表
        
        Args:
            limit: 获取的邮件数量
            hours: 获取指定小时数内的邮件
        """
        try:
            # 构建查询参数
            filter_params = []
            if hours:
                time_filter = timezone.now() - timedelta(hours=hours)
                filter_params.append(f"receivedDateTime ge {time_filter.isoformat()}Z")

            # 构建查询URL
            url = f"{self.GRAPH_API_BASE}/users/{self.user_mail.email}/messages"
            params = {
                '$select': 'id,subject,sender,receivedDateTime,body,categories,importance,hasAttachments',
                '$orderby': 'receivedDateTime DESC',
                '$top': limit if limit else 50,
                '$expand': 'attachments'  # 添加附件展开
            }
            if filter_params:
                params['$filter'] = ' and '.join(filter_params)

            # 发送请求
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            emails_data = response.json().get('value', [])

            # 处理邮件数据
            processed_emails = []
            for email_data in emails_data:
                # 检查邮件是否已存在
                existing_email = CCEmail.objects.filter(
                    message_id=email_data['id'],
                    user_mail=self.user_mail
                ).first()

                if existing_email:
                    if not existing_email.is_read:
                        # 标记为已读
                        self._mark_as_read(email_data['id'])
                        existing_email.is_read = True
                        existing_email.save()
                    processed_emails.append(existing_email)
                    continue

                # 创建新的邮件记录
                email = CCEmail.objects.create(
                    user_mail=self.user_mail,
                    message_id=email_data['id'],
                    subject=email_data['subject'],
                    sender=email_data['sender']['emailAddress']['address'],
                    received_time=datetime.fromisoformat(email_data['receivedDateTime'].replace('Z', '+00:00')),
                    content=email_data['body']['content'],
                    categories=','.join(email_data.get('categories', [])),
                    importance=email_data['importance'],
                    has_attachments=email_data['hasAttachments'],
                    is_read=True
                )

                # 更新附件信息
                if email_data['hasAttachments']:
                    attachments = email_data.get('attachments', [])
                    email.update_attachment_info(attachments)
                    email.save()

                # 标记为已读
                self._mark_as_read(email_data['id'])
                processed_emails.append(email)

            # 更新最后同步时间
            self.user_mail.last_sync_time = timezone.now()
            self.user_mail.save(update_fields=['last_sync_time'])

            return processed_emails

        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            raise

    def _mark_as_read(self, message_id: str) -> None:
        """标记邮件为已读"""
        try:
            url = f"{self.GRAPH_API_BASE}/users/{self.user_mail.email}/messages/{message_id}"
            data = {
                "isRead": True
            }
            response = requests.patch(url, headers=self._get_headers(), json=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error marking email as read: {str(e)}")
            raise 