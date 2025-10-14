from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/python/code/(?P<session_id>[0-9a-f-]+)/$', consumers.CollaborativeSessionConsumer.as_asgi()),
]
