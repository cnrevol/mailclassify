from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/email_monitor/(?P<email>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})/$', 
            consumers.EmailMonitorConsumer.as_asgi()),
] 