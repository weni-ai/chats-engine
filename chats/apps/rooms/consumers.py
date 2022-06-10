import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer


from chats.apps.rooms.models import Room
from chats.apps.msgs.models import Message as ChatMessage


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            self.username = "guest"
            self.room = await database_sync_to_async(self.create_room)()
        else:
            self.username = self.user.email
            self.room = await database_sync_to_async(self.get_room)(
                self.scope["url_route"]["kwargs"]["room_name"]
            )
        self.room_group_name = "chat_%s" % self.room.pk

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        self.recieved_data = json.loads(text_data)
        message = self.recieved_data["message"]
        self.message = f"{self.username}: {message}"

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": self.message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    def create_room(self):
        return Room.objects.create(is_active=True)

    def get_room(self, pk):
        try:
            room = Room.objects.get(pk=pk)
        except (Room.DoesNotExist, ValueError):
            raise (StopConsumer)
        return room
