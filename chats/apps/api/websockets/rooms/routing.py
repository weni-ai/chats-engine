from django.urls import re_path

from chats.apps.api.websockets.rooms.consumers import agent, contact

websocket_urlpatterns = [
    re_path(r"ws/agent/rooms", agent.AgentRoomConsumer.as_asgi()),
    re_path(
        r"ws/contact/room/(?P<room>[0-9a-f-]+)/$", contact.ContactRoomConsumer.as_asgi()
    ),
]
