import logging
import json
import time
from django.conf import settings

logger = logging.getLogger('core')

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 开始时间
        start_time = time.time()

        # 记录请求信息
        self.log_request(request)

        # 获取响应
        response = self.get_response(request)

        # 计算处理时间
        duration = time.time() - start_time

        # 记录响应信息
        self.log_response(request, response, duration)

        return response

    def log_request(self, request):
        """记录请求信息"""
        try:
            # 获取请求体（如果有）
            body = None
            if request.body:
                try:
                    body = json.loads(request.body)
                except json.JSONDecodeError:
                    body = request.body.decode('utf-8')

            log_data = {
                'remote_address': request.META.get('REMOTE_ADDR'),
                'server_hostname': request.META.get('SERVER_NAME'),
                'request_method': request.method,
                'request_path': request.get_full_path(),
                'request_body': body,
                'user': str(request.user),
            }

            logger.info(f"Request: {json.dumps(log_data, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")

    def log_response(self, request, response, duration):
        """记录响应信息"""
        try:
            # 获取响应体（如果可能）
            response_body = None
            if hasattr(response, 'content'):
                try:
                    response_body = json.loads(response.content)
                except:
                    response_body = response.content.decode('utf-8')

            log_data = {
                'request_path': request.get_full_path(),
                'response_status': response.status_code,
                'duration': f"{duration:.2f}s",
                'content_length': len(response.content) if hasattr(response, 'content') else 0,
                'response_body': response_body if settings.DEBUG else None,  # 只在DEBUG模式记录响应体
            }

            logger.info(f"Response: {json.dumps(log_data, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"Error logging response: {str(e)}") 