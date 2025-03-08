from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from .serializers import (
    RegisterSerializer, 
    UserSerializer, 
    CCUserMailInfoSerializer,
    CCAzureOpenAISerializer,
    CCOpenAISerializer,
    CCEmailSerializer
)
from .models import CCUserMailInfo, CCAzureOpenAI, CCOpenAI, CCEmail
from .llm_factory import LLMFactory
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .services.mail_service import OutlookMailService
import logging
from .chat_service import ChatService
import requests
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.http import HttpResponseRedirect
import uuid
from urllib.parse import urlencode
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

# 获取logger
logger = logging.getLogger('core')

# Create your views here.

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        logger.info(f"Creating new user: {serializer.validated_data.get('username')}")
        try:
            user = serializer.save()
            logger.info(f"Successfully created user: {user.username}")
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        logger.debug(f"Retrieving user details for: {self.request.user.username}")
        return self.request.user

    def update(self, request, *args, **kwargs):
        logger.info(f"Updating user details for: {request.user.username}")
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"Successfully updated user: {request.user.username}")
            return response
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise

class CCUserMailInfoViewSet(generics.GenericAPIView):
    queryset = CCUserMailInfo.objects.all()
    serializer_class = CCUserMailInfoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """获取邮件信息列表"""
        logger.debug("Retrieving all mail info")
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """创建邮件信息"""
        logger.info(f"Creating mail info with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Successfully created mail info for: {request.data.get('email')}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Failed to create mail info: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CCUserMailInfoDetailView(generics.GenericAPIView):
    queryset = CCUserMailInfo.objects.all()
    serializer_class = CCUserMailInfoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        """获取单个邮件信息"""
        try:
            instance = self.get_queryset().get(pk=pk)
            logger.debug(f"Retrieving mail info for id: {pk}")
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except CCUserMailInfo.DoesNotExist:
            logger.error(f"Mail info not found for id: {pk}")
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        """更新邮件信息"""
        try:
            instance = self.get_queryset().get(pk=pk)
            logger.info(f"Updating mail info for id: {pk}")
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Successfully updated mail info for id: {pk}")
                return Response(serializer.data)
            logger.error(f"Failed to update mail info: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CCUserMailInfo.DoesNotExist:
            logger.error(f"Mail info not found for id: {pk}")
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        """删除邮件信息"""
        try:
            instance = self.get_queryset().get(pk=pk)
            logger.info(f"Deleting mail info for id: {pk}")
            instance.delete()
            logger.info(f"Successfully deleted mail info for id: {pk}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CCUserMailInfo.DoesNotExist:
            logger.error(f"Mail info not found for id: {pk}")
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

class LLMBaseView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_llm_instance(self, provider: str, instance_id: int):
        return LLMFactory.get_instance_by_id(provider, instance_id)

class AzureOpenAIViewSet(ModelViewSet):
    queryset = CCAzureOpenAI.objects.all()
    serializer_class = CCAzureOpenAISerializer
    permission_classes = (permissions.IsAuthenticated,)

class OpenAIViewSet(ModelViewSet):
    queryset = CCOpenAI.objects.all()
    serializer_class = CCOpenAISerializer
    permission_classes = (permissions.IsAuthenticated,)

class LLMCompletionView(LLMBaseView):
    def post(self, request, provider, instance_id):
        """
        获取LLM补全结果
        """
        prompt = request.data.get('prompt')
        if not prompt:
            return Response(
                {'error': 'Prompt is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        llm = self.get_llm_instance(provider, instance_id)
        if not llm:
            return Response(
                {'error': 'LLM instance not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            response = llm.get_completion(prompt)
            return Response({'response': response})
        except Exception as e:
            logger.error(f"Error getting completion: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OutlookMailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        获取邮件列表
        
        参数:
        - email: 邮箱地址
        - limit: 获取的邮件数量（可选）
        - hours: 获取指定小时数内的邮件（可选）
        """
        try:
            email = request.query_params.get('email')
            if not email:
                return Response(
                    {'error': 'Email parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 获取用户邮件配置
            user_mail = CCUserMailInfo.objects.filter(email=email, is_active=True).first()
            if not user_mail:
                return Response(
                    {'error': 'Email configuration not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # 获取查询参数
            limit = request.query_params.get('limit')
            hours = request.query_params.get('hours')

            # 转换参数类型
            if limit:
                try:
                    limit = int(limit)
                except ValueError:
                    return Response(
                        {'error': 'Invalid limit parameter'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if hours:
                try:
                    hours = int(hours)
                except ValueError:
                    return Response(
                        {'error': 'Invalid hours parameter'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 获取邮件
            mail_service = OutlookMailService(user_mail)
            emails = mail_service.fetch_emails(limit=limit, hours=hours)

            # 序列化结果
            serializer = CCEmailSerializer(emails, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OutlookOAuthView(APIView):
    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_auth_url(request):
        """
        获取 OAuth 授权 URL
        
        参数:
        - email: 邮箱地址
        - email_id: 邮箱配置ID
        """
        try:
            email = request.query_params.get('email')
            email_id = request.query_params.get('email_id')
            
            if not email:
                return Response(
                    {'error': '邮箱地址参数是必需的'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if not email_id:
                return Response(
                    {'error': '邮箱配置ID是必需的'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # 获取用户邮件配置
            user_mail = CCUserMailInfo.objects.filter(email=email, is_active=True).first()
            if not user_mail:
                return Response(
                    {'error': '未找到邮箱配置'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 构建回调 URL，强制使用 localhost，并添加 email_id 参数
            callback_uri = request.build_absolute_uri(settings.OAUTH_SETTINGS['redirect_path'])
            callback_uri = callback_uri.replace('127.0.0.1', 'localhost')
            if '?' in callback_uri:
                callback_uri += f'&email_id={email_id}'
            else:
                callback_uri += f'?email_id={email_id}'
                
            # 构建授权参数
            auth_params = {
                'client_id': user_mail.client_id,
                'response_type': 'code',
                'redirect_uri': callback_uri,
                'scope': ' '.join(settings.OAUTH_SETTINGS['scope']),
                'response_mode': 'query',
                'access_type': 'offline',  # 明确请求离线访问
                'prompt': 'consent'  # 强制显示同意页面，确保获取刷新令牌
            }
            
            # 构建授权 URL
            auth_url = (
                f"{settings.OAUTH_SETTINGS['authority']}"
                f"{settings.OAUTH_SETTINGS['authorize_endpoint']}?"
                f"{urlencode(auth_params)}"
            )
            
            logger.info(f"生成授权 URL，参数: {auth_params}")
            logger.debug(f"完整授权 URL: {auth_url}")
            
            return Response({'auth_url': auth_url})
            
        except Exception as e:
            logger.error(f"生成授权 URL 时出错: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @staticmethod
    @api_view(['GET'])
    @permission_classes([AllowAny])
    @authentication_classes([])
    def handle_callback(request):
        """
        处理 OAuth 回调
        """
        try:
            logger.info("收到 OAuth 回调")
            logger.info(f"查询参数: {request.GET}")
            
            # 检查是否有错误
            error = request.GET.get('error')
            error_description = request.GET.get('error_description')
            if error:
                logger.error(f"OAuth 授权错误: {error} - {error_description}")
                return Response({
                    'error': error,
                    'error_description': error_description
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # 获取授权码
            code = request.GET.get('code')
            if not code:
                logger.error("未收到授权码")
                return Response({
                    'error': 'no_code',
                    'error_description': '未收到授权码'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 从查询参数中获取邮箱 ID
            email_id = request.GET.get('email_id')
            if not email_id:
                logger.error("未提供邮箱 ID")
                return Response({
                    'error': 'no_email_id',
                    'error_description': '未提供邮箱 ID'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # 获取用户邮件配置
            try:
                user_mail = CCUserMailInfo.objects.get(id=email_id)
            except CCUserMailInfo.DoesNotExist:
                logger.error(f"未找到 ID 为 {email_id} 的邮箱配置")
                return Response({
                    'error': 'email_not_found',
                    'error_description': '未找到邮箱配置'
                }, status=status.HTTP_404_NOT_FOUND)
                
            # 使用授权码获取访问令牌
            token_url = f"{settings.OAUTH_SETTINGS['authority']}{settings.OAUTH_SETTINGS['token_endpoint']}"
            
            # 构建回调 URL，强制使用 localhost，并添加 email_id 参数
            callback_uri = request.build_absolute_uri(settings.OAUTH_SETTINGS['redirect_path'])
            callback_uri = callback_uri.replace('127.0.0.1', 'localhost')
            if '?' in callback_uri:
                callback_uri += f'&email_id={email_id}'
            else:
                callback_uri += f'?email_id={email_id}'
            
            token_data = {
                'client_id': user_mail.client_id,
                'client_secret': user_mail.client_secret,
                'scope': ' '.join(settings.OAUTH_SETTINGS['scope']),
                'code': code,
                'redirect_uri': callback_uri,
                'grant_type': 'authorization_code',
            }
            
            logger.info("使用配置的凭据请求令牌")
            
            # 发送请求获取令牌
            token_response = requests.post(token_url, data=token_data)
            logger.info(f"令牌响应状态: {token_response.status_code}")
            
            if token_response.status_code == 200:
                tokens = token_response.json()
                logger.info("成功获取令牌")
                logger.debug(f"令牌响应内容: {tokens.keys()}")  # 只记录键名，不记录敏感信息
                
                # 更新用户邮件配置
                try:
                    user_mail.access_token = tokens['access_token']
                    if 'refresh_token' in tokens:
                        user_mail.refresh_token = tokens['refresh_token']
                    user_mail.token_expires = timezone.now() + timedelta(seconds=tokens['expires_in'])
                    user_mail.save(update_fields=['access_token', 'refresh_token', 'token_expires'])
                    
                    logger.info(f"成功更新 {user_mail.email} 的令牌")
                except Exception as e:
                    logger.error(f"保存令牌时出错: {str(e)}")
                    return Response({
                        'error': 'token_save_error',
                        'error_description': '保存令牌时出错'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # 重定向到前端页面
                redirect_url = settings.OAUTH_SETTINGS['frontend_redirect_url']
                if not redirect_url.endswith('/'):
                    redirect_url += '/'
                redirect_url += "chat?menu=mail-config&auth_success=true"
                logger.info(f"重定向到: {redirect_url}")
                
                return redirect(redirect_url)
            else:
                logger.error(f"令牌请求失败: {token_response.text}")
                try:
                    error_data = token_response.json()
                    error_description = error_data.get('error_description', token_response.text)
                except Exception:
                    error_description = token_response.text
                
                return Response({
                    'error': 'token_error',
                    'error_description': f'获取访问令牌失败: {error_description}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"处理 OAuth 回调时出错: {str(e)}", exc_info=True)
            return Response({
                'error': 'server_error',
                'error_description': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_user_info(access_token):
        """获取用户信息"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"获取用户信息时出错: {str(e)}")
            return None

class ClassifyEmailsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        对邮件进行分类
        """
        try:
            # 获取请求参数
            email = request.data.get('email')
            hours = request.data.get('hours', 2)  # 默认获取2小时内的邮件
            method = request.data.get('method', 'stepgo')  # 默认使用 stepgo 分类
            
            if not email:
                return Response(
                    {'error': 'Email is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            logger.info(f"开始处理邮件分类请求，邮箱: {email}, 方法: {method}, 时间范围: {hours}小时")
            
            # 获取用户邮件配置
            user_mail = CCUserMailInfo.objects.filter(email=email, is_active=True).first()
            if not user_mail:
                logger.error(f"未找到邮箱配置: {email}")
                return Response(
                    {'error': 'Email configuration not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 1. 从 Outlook 获取邮件
            logger.info(f"开始从 Outlook 获取 {email} 的邮件")
            mail_service = OutlookMailService(user_mail)
            emails = mail_service.fetch_emails(hours=hours)
            logger.info(f"成功获取 {len(emails)} 封邮件")
            
            if not emails:
                logger.info("没有新邮件需要分类")
                return Response({
                    'status': 'success',
                    'message': '没有新邮件需要分类',
                    'classified_count': 0
                })

            # 2. 对邮件进行分类
            logger.info(f"开始使用 {method} 方法对邮件进行分类")
            from core.services.email_classifier import EmailClassifier
            results = EmailClassifier.classify_emails(emails, method=method)
            
            # 3. 统计分类结果
            total_classified = 0
            classification_stats = {}
            
            for classification, emails_data in results.items():
                classification_stats[classification] = len(emails_data)
                total_classified += len(emails_data)
                
                # 更新邮件分类
                for data in emails_data:
                    # 获取邮件对象
                    if 'email' in data:
                        email_obj = data['email']
                        email_obj.categories = classification
                        email_obj.save(update_fields=['categories'])
                        logger.debug(f"邮件 '{email_obj.subject[:30]}...' 分类为 '{classification}'")
                    else:
                        logger.warning(f"邮件数据中缺少 'email' 字段: {data}")
            
            logger.info(f"分类完成，共分类 {total_classified} 封邮件")
            
            return Response({
                'status': 'success',
                'message': f'成功分类 {total_classified} 封邮件',
                'classified_count': total_classified,
                'classification_stats': classification_stats
            })

        except Exception as e:
            logger.error(f"邮件分类过程中出错: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChatView(APIView):
    """
    Chat API endpoint
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_service = ChatService()

    def post(self, request, *args, **kwargs):
        """
        Handle chat message
        """
        message = request.data.get('message')
        model = request.data.get('model')

        if not message:
            return Response(
                {'error': 'Message is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process message
        response = self.chat_service.process_message(message, model)
        formatted_response = self.chat_service.format_response(response)

        return Response(
            formatted_response,
            status=status.HTTP_200_OK if formatted_response['success'] 
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
