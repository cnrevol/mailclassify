from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),  # API endpoints will be under /api/
    path('api/mail/monitor/', views.EmailMonitorView.as_view(), name='mail-monitor'),
]

# WebSocket URLs are handled by the ASGI application in config/asgi.py
# The actual WebSocket routing is defined in core/routing.py 