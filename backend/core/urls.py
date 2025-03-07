from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterView, 
    UserDetailView, 
    CCUserMailInfoViewSet,
    CCUserMailInfoDetailView,
    AzureOpenAIViewSet,
    OpenAIViewSet,
    LLMCompletionView,
    OutlookMailView,
    ChatView
)

app_name = 'core'

# 创建路由器
router = DefaultRouter()
router.register(r'llm/azure', AzureOpenAIViewSet, basename='azure-openai')
router.register(r'llm/openai', OpenAIViewSet, basename='openai')

urlpatterns = [
    # 认证相关的URL
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('user/', UserDetailView.as_view(), name='user_detail'),
    
    # 邮件信息相关的URL
    path('mail-info/', CCUserMailInfoViewSet.as_view(), name='mail_info_list'),
    path('mail-info/<int:pk>/', CCUserMailInfoDetailView.as_view(), name='mail_info_detail'),

    # LLM补全接口
    path('llm/<str:provider>/<int:instance_id>/completion/', 
         LLMCompletionView.as_view(), 
         name='llm_completion'),

    # 邮件相关的URL
    path('mail/outlook/', OutlookMailView.as_view(), name='outlook_mail'),

    # 聊天接口
    path('chat/', ChatView.as_view(), name='chat'),

    # 包含自动生成的路由
    path('', include(router.urls)),
] 