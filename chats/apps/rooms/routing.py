from django.urls import re_path

from chats.apps.rooms import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.RoomConsumer.as_asgi()),
]
