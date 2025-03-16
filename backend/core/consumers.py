import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .models import CCEmail, CCEmailMonitorStatus, CCEmailClassifyRule, CCForwardingAddress, CCForwardingRule
from .services.email_monitor import EmailMonitorService

logger = logging.getLogger(__name__)

class EmailMonitorConsumer(AsyncWebsocketConsumer):
    """Email monitoring WebSocket consumer"""
    
    @staticmethod
    def get_group_name(email: str) -> str:
        """Convert email to valid group name by replacing @ with _at_ and . with _dot_"""
        return f'email_monitor_{email.replace("@", "_at_").replace(".", "_dot_")}'
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.email = self.scope['url_route']['kwargs']['email']
        self.room_group_name = self.get_group_name(self.email)
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Start monitoring loop
        asyncio.create_task(self.monitoring_loop())
        
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Stop monitoring
        await database_sync_to_async(EmailMonitorService.stop_monitoring)(self.email)
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'start_monitoring':
                await database_sync_to_async(EmailMonitorService.start_monitoring)(self.email)
            elif action == 'stop_monitoring':
                await database_sync_to_async(EmailMonitorService.stop_monitoring)(self.email)
            elif action == 'get_status':
                status = await database_sync_to_async(self.get_monitoring_status)()
                await self.send_status(status)
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    @staticmethod
    def get_monitoring_status():
        """获取监控状态"""
        try:
            # 获取所有邮件（包括未处理的）
            total_emails = CCEmail.objects.all()
            
            # 获取已接收的邮件（所有邮件都是已接收的）
            received_emails = total_emails.count()
            
            # 获取已处理（分类完成）的邮件
            processed_emails = CCEmail.objects.filter(
                is_processed=True
            )
            
            # 获取已转发的邮件
            forwarded_emails = CCEmail.objects.filter(
                is_forwarded=True
            )
            
            # 获取分类统计
            classification_stats = {}
            rules = CCEmailClassifyRule.objects.filter(is_active=True)
            rule_names = {rule.classification: rule.name for rule in rules}
            
            # 获取每个分类的转发地址
            forwarding_addresses = {}
            for rule in rules:
                # 获取对应的 email_types
                email_types = settings.EMAIL_TYPE_MAPPING.get(rule.classification.lower(), [])
                logger.debug(f"规则 '{rule.name}' 映射的邮件类型: {email_types}")
                
                if not email_types:
                    logger.warning(f"规则 '{rule.name}' 没有映射的邮件类型")
                    continue
                
                # 对每个 email_type 查找转发规则和地址
                for email_type in email_types:
                    forwarding_rule = CCForwardingRule.objects.filter(
                        email_type=email_type,
                        is_active=True
                    ).first()
                    
                    if forwarding_rule:
                        addresses = CCForwardingAddress.objects.filter(
                            rule=forwarding_rule,
                            is_active=True
                        ).values_list('name', flat=True)
                        if addresses:
                            forwarding_addresses[rule.classification] = addresses[0]
                            logger.debug(f"规则 '{rule.name}' 的转发地址: {addresses[0]}")
                            break  # 找到第一个有效的转发地址就跳出
                        else:
                            logger.warning(f"邮件类型 '{email_type}' 没有找到活动的转发地址")
                    else:
                        logger.warning(f"邮件类型 '{email_type}' 没有找到对应的转发规则")
            
            # 统计每个分类的邮件数量
            for email in processed_emails:
                if email.categories:  # 使用 categories 字段
                    category_name = rule_names.get(email.categories, email.categories)
                    forwarding_name = forwarding_addresses.get(email.categories, '')
                    key = f"{category_name} ({forwarding_name})" if forwarding_name else category_name
                    classification_stats[key] = classification_stats.get(key, 0) + 1
                    
            # 添加调试日志
            logger.debug(f"分类统计: {classification_stats}")
            logger.debug(f"转发地址映射: {forwarding_addresses}")
            
            return {
                'total_emails': total_emails.count(),
                'received_emails': received_emails,
                'processed_emails': processed_emails.count(),
                'forwarded_emails': forwarded_emails.count(),
                'classification_stats': classification_stats
            }
        except Exception as e:
            logger.error(f"获取监控状态时出错: {str(e)}", exc_info=True)
            return {
                'total_emails': 0,
                'received_emails': 0,
                'processed_emails': 0,
                'forwarded_emails': 0,
                'classification_stats': {}
            }
    
    async def monitoring_loop(self):
        """Periodic monitoring loop"""
        while True:
            try:
                # Check monitoring status
                status = await database_sync_to_async(EmailMonitorService.get_monitoring_status)(self.email)
                
                if not status.get('is_monitoring'):
                    await asyncio.sleep(1)
                    continue
                
                # Check for new emails
                result = await database_sync_to_async(EmailMonitorService.check_new_emails)(
                    self.email,
                    check_interval_minutes=0  # Ignore time interval check
                )
                
                # Get updated status
                status = await database_sync_to_async(self.get_monitoring_status)()
                await self.send_status(status)
                
                # Send log message if available
                if result.get('message'):
                    # 不直接发送消息，而是通过logger发送，这样会自动添加时间戳
                    logger.info(result['message'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}", exc_info=True)
                await self.send_log(f"Error: {str(e)}")
            
            # Wait for next check
            await asyncio.sleep(settings.EMAIL_MONITOR_INTERVAL)
    
    async def send_status(self, status):
        """Send status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': status
        }))
    
    async def send_log(self, message):
        """Send log message to WebSocket"""
        try:
            if isinstance(message, str):
                # 如果是字符串，直接发送
                await self.send(text_data=json.dumps({
                    'type': 'log_message',
                    'message': message
                }))
            elif isinstance(message, dict):
                # 如果是字典，转换为JSON
                await self.send(text_data=json.dumps({
                    'type': 'log_message',
                    'message': json.dumps(message)
                }))
        except Exception as e:
            logger.error(f"Error sending log message: {str(e)}", exc_info=True)
    
    async def log_message(self, event):
        """Handle log message from group"""
        try:
            # 直接转发消息到客户端
            await self.send(text_data=json.dumps({
                'type': 'log_message',
                'message': event['message']
            }))
        except Exception as e:
            logger.error(f"Error sending log message: {str(e)}", exc_info=True) 