from django.urls import re_path

from chats.apps.api.websockets.rooms.consumers import agent, contact

websocket_urlpatterns = [
    re_path(r"ws/agent/rooms", agent.AgentRoomConsumer.as_asgi()),
    re_path(
        r"ws/contact/rooms/(?P<room_id>\w+)/$", contact.ContactRoomConsumer.as_asgi()
    ),
]
