from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterView, 
    UserDetailView, 
    CCUserMailInfoViewSet,
    CCUserMailInfoDetailView
)

app_name = 'core'

urlpatterns = [
    # Add your API endpoints here
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('user/', UserDetailView.as_view(), name='user_detail'),
    
    # 邮件信息相关的URL
    path('mail-info/', CCUserMailInfoViewSet.as_view(), name='mail_info_list'),
    path('mail-info/<int:pk>/', CCUserMailInfoDetailView.as_view(), name='mail_info_detail'),
] 