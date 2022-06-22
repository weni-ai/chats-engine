import json

from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.rooms.models import Room
from chats.apps.contacts.models import Contact


GET = 0
CREATE = 1
UPDATE = 2
DELETE = 3


class ChatConsumer(AsyncJsonWebsocketConsumer):
    EMPLOYEE = 2
    CLIENT = 1

    async def connect(self, *args, **kwargs):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        # Are they logged in?
        if self.scope["user"].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            await self.accept()

        await self.agent_load_inital_rooms()
        await self.agent_notification_room()

    async def disconnect(self, close_code):
        if not self.scope["user"].is_anonymous:

            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive_json(self, content):
        typ = content.get("type")
        if typ == "message":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": self.scope["user"].get_full_name(),
                    "message": content["message"],
                },
            )

    async def chat_message(self, event):
        await self.send_json(event)

    async def chat_join(self, event):
        await self.send_json(event)

    async def chat_leave(self, event):
        await self.send_json(event)
