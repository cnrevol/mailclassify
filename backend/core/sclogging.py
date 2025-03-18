import logging
import json
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Optional
from datetime import datetime
import threading


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that forwards logs to WebSocket clients"""
    
    def __init__(self, email: str):
        super().__init__()
        self.email = email
        self.channel_layer = get_channel_layer()
        # Generate room group name directly
        self.room_group_name = f'email_monitor_{self.email.replace("@", "_at_").replace(".", "_dot_")}'
        
    def emit(self, record):
        """Emit a log record"""
        try:
            # Format the log message
            msg = self.format(record)
            
            # Create a structured log message
            log_data = {
                'timestamp': record.created,
                'level': record.levelname,
                'logger': record.name,
                'process': record.process,
                'thread': record.thread,
                'message': msg
            }
            
            # Send to WebSocket group
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'log_message',
                    'message': msg  # 直接发送格式化后的消息，而不是JSON
                }
            )
        except Exception:
            self.handleError(record)

class WebSocketLogger:
    """Wrapper class for logging with WebSocket support"""
    
    _instance_lock = threading.Lock()
    _instances = {}
    
    def __new__(cls, name: str, email: Optional[str] = None):
        # 使用线程安全的单例模式
        key = f"{name}:{email}"
        with cls._instance_lock:
            if key not in cls._instances:
                cls._instances[key] = super().__new__(cls)
            return cls._instances[key]
    
    def __init__(self, name: str, email: Optional[str] = None):
        if not hasattr(self, 'initialized'):
            self.logger = logging.getLogger(name)
            self.email = email
            self.local = threading.local()
            
            if email:
                # Check if WebSocket handler already exists
                has_ws_handler = any(
                    isinstance(handler, WebSocketLogHandler) and handler.email == email
                    for handler in self.logger.handlers
                )
                
                if not has_ws_handler:
                    # Add WebSocket handler only if it doesn't exist
                    ws_handler = WebSocketLogHandler(email)
                    ws_handler.setFormatter(logging.Formatter(
                        '[%(asctime)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                    ))
                    self.logger.addHandler(ws_handler)
            
            self.initialized = True
    
    def _log_and_send(self, level: str, message: str, *args, **kwargs):
        """记录日志并通过WebSocket发送"""
        # 添加线程标识到消息中
        thread_name = threading.current_thread().name
        formatted_message = f"[Thread-{thread_name}] {message}"
        
        # 通过标准日志记录
        getattr(self.logger, level)(formatted_message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self._log_and_send('debug', message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self._log_and_send('info', message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self._log_and_send('warning', message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self._log_and_send('error', message, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        """Log exception message"""
        self.logger.exception(msg, *args, **kwargs) 