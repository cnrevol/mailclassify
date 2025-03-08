import logging
import requests
from typing import Dict, List, Any, Optional
from django.utils import timezone
from datetime import timedelta
from ..models import CCUserMailInfo

logger = logging.getLogger(__name__)

class GraphService:
    """Microsoft Graph API 服务类"""
    
    GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'
    AUTH_BASE = 'https://login.microsoftonline.com'
    SCOPE = 'https://graph.microsoft.com/Mail.ReadWrite'
    
    def __init__(self, user_mail: CCUserMailInfo):
        """
        初始化 Graph API 服务
        
        Args:
            user_mail: 用户邮件配置信息
        """
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
    
    def forward_email(self, email_id: str, to_recipients: List[Dict[str, str]], forward_comment: str = "") -> Dict[str, Any]:
        """
        转发邮件
        
        Args:
            email_id: 邮件ID
            to_recipients: 收件人列表，格式为 [{'email': 'email@example.com', 'name': 'Name'}]
            forward_comment: 转发附言
            
        Returns:
            转发结果
        """
        try:
            url = f"{self.GRAPH_API_BASE}/users/{self.user_mail.email}/messages/{email_id}/forward"
            
            # 构建收件人格式
            formatted_recipients = [
                {
                    "emailAddress": {
                        "address": recipient['email'],
                        "name": recipient.get('name', recipient['email'])
                    }
                }
                for recipient in to_recipients
            ]
            
            # 构建请求数据
            data = {
                "toRecipients": formatted_recipients,
                "comment": forward_comment
            }
            
            logger.debug(f"转发邮件: {url}")
            logger.debug(f"收件人: {formatted_recipients}")
            
            # 发送请求
            response = requests.post(url, headers=self._get_headers(), json=data)
            response.raise_for_status()
            
            logger.info(f"成功转发邮件 {email_id} 给 {', '.join([r['email'] for r in to_recipients])}")
            return {
                'success': True,
                'message': f"成功转发邮件给 {len(to_recipients)} 个收件人"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"转发邮件时出错: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"转发邮件时出错: {str(e)}"
            }
        except Exception as e:
            logger.error(f"转发邮件时出现意外错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"转发邮件时出现意外错误: {str(e)}"
            } 