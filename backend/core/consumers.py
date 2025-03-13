import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .models import CCEmail, CCEmailMonitorStatus
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
    
    @staticmethod
    def get_monitoring_status():
        """Get current monitoring status"""
        total_emails = CCEmail.objects.count()
        processing_emails = CCEmail.objects.filter(is_processed=False).count()
        processed_emails = CCEmail.objects.filter(is_processed=True).count()
        
        # Get classification stats
        classification_stats = {}
        for category in CCEmail.objects.exclude(categories='').values('categories').distinct():
            category_name = category['categories']
            count = CCEmail.objects.filter(categories=category_name).count()
            classification_stats[category_name] = count
        
        return {
            'total_emails': total_emails,
            'processing_emails': processing_emails,
            'processed_emails': processed_emails,
            'classification_stats': classification_stats
        }
    
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