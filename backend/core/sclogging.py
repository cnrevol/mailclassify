import logging
import json
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Optional
from .consumers import EmailMonitorConsumer

class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that forwards logs to WebSocket clients"""
    
    def __init__(self, email: str):
        super().__init__()
        self.email = email
        self.channel_layer = get_channel_layer()
        self.room_group_name = f'email_monitor_{self.email}'
        
    def emit(self, record):
        """Emit a log record"""
        try:
            # Format the log message
            msg = self.format(record)
            
            # Send to WebSocket group
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'log_message',
                    'message': msg
                }
            )
        except Exception:
            self.handleError(record)

class WebSocketLogger:
    """Wrapper class for logging with WebSocket support"""
    
    def __init__(self, name: str, email: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.email = email
        
        if email:
            # Add WebSocket handler
            ws_handler = WebSocketLogHandler(email)
            ws_handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(ws_handler)
    
    def debug(self, msg, *args, **kwargs):
        """Log debug message"""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        """Log info message"""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """Log warning message"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """Log error message"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        """Log exception message"""
        self.logger.exception(msg, *args, **kwargs) 