from django.urls import re_path

from chats.apps.api.websockets.rooms.consumers import agent


websocket_urlpatterns = [
    re_path(r"ws/chat/", agent.AgentRoomConsumer.as_asgi()),
]
