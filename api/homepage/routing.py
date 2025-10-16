from django.urls import re_path
from . import consumers
from . import ide_consumers  # Import IDE consumers

websocket_urlpatterns = [
    # Collaborative Python environment sessions
    re_path(r'ws/python/code/(?P<session_id>[0-9a-f-]+)/$', consumers.CollaborativeSessionConsumer.as_asgi()),
    
    # Cloud IDE WebSocket routes (for paid users)
    re_path(r'ws/ide/terminal/(?P<project_id>[0-9a-f-]+)/$', ide_consumers.IDETerminalConsumer.as_asgi()),
    re_path(r'ws/ide/collaboration/(?P<project_id>[0-9a-f-]+)/$', ide_consumers.IDECollaborationConsumer.as_asgi()),
]
