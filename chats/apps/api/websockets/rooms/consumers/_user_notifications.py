import json

from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer

from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.rooms.models import Room
from chats.apps.contacts.models import Contact


GET = 0
CREATE = 1
UPDATE = 2
DELETE = 3


class RoomConsumer(AsyncWebsocketConsumer):
    # Receive message from WebSocket
    async def connect(self):
        self.user = self.scope["user"]
        self.contact = None
        self.room = None
        self.username = None

        try:
            self.username = self.user.email
            self.room = await self._room(
                operation=GET, pk=self.scope["url_route"]["kwargs"]["room_name"]
            )

        except AttributeError:
            self.username = "guest"
            self.room = await self._room(operation=CREATE)

        self.room_group_name = "chat_%s" % self.room.pk

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group

        if self.username == "guest":
            await self._room(operation=DELETE)
        else:
            await self._room(operation=UPDATE, field="is_active", value=False)

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        recieved_data = json.loads(text_data)
        message = recieved_data["message"]
        self.message = f"{self.username}: {message}"

        if self.contact is not None or self.user.is_anonymous is False:
            await self.create_message(message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": self.message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data="json.dumps({'message': message})")

    @database_sync_to_async
    def create_contact(self, info):
        self.contact = Contact.objcets.get_or_create(**info)

        self.username = info["username"]

    @database_sync_to_async
    def create_message(self, message):
        msg = None
        if self.user.is_anonymous:
            msg = ChatMessage.objects.create(
                room=self.room, contact=self.contact, text=message
            )
        else:
            msg = ChatMessage.objects.create(
                room=self.room, user=self.user, text=message
            )
        return msg

    @database_sync_to_async
    def _room(self, operation, pk=None, **kwargs):
        try:
            if operation == GET:
                self.room = Room.objects.get(pk=pk)
                if self.room.user is None:
                    self._room(operation=UPDATE, field="user", value=self.user)
                elif self.room.user == self.user:
                    pass
                else:
                    raise (StopConsumer)

            elif operation == CREATE:
                return Room.objects.create(is_active=True)
            elif operation == UPDATE:
                setattr(self.room, kwargs["field"], kwargs["value"])
                self.room.save()
                return self.room
            elif operation == DELETE:
                self.room.delete()
                return None
        except (Room.DoesNotExist, ValueError):
            raise (StopConsumer)
        return self.room
