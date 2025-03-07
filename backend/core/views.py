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
