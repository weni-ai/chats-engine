import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder

from chats.apps.api.v1.msgs.serializers import MessageWSSerializer
from chats.apps.rooms.models import Room


# TODO Use this on the agent consumer and move it to another place
class BaseWebsocketConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def encode_json(cls, content):
        return json.dumps(content, cls=DjangoJSONEncoder)


class ContactRoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.contact = None
        self.room = self.scope["url_route"]["kwargs"]["room"]
        self.order_by = self.scope["query_params"].get("order_by")[0]

        self.room_group_name = f"room_{self.room}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.get_room()

        await self.accept()
        # await self.get_msgs()
        await self.send_msgs()

    async def disconnect(self, close_code):
        # Leave room group

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, payload):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        command_name = payload.get("type", None)
        if command_name == "notify":
            await self.notify(payload["content"])
        elif command_name == "method":
            command = getattr(self, payload["action"])
            await command(payload["content"])

    async def notify(self, event):
        await self.send_json(json.dumps(event["content"]))

    @database_sync_to_async
    def get_room(self):
        self.room = Room.objects.get(pk=self.room)
        self.contact = self.room.contact
        return self.room

    @database_sync_to_async
    def get_msgs(self):
        msgs = self.room.messages.all().order_by(self.order_by)
        self.serialized_messages = MessageWSSerializer(msgs, many=True).data

        return json.dumps(self.serialized_messages, cls=DjangoJSONEncoder)

    async def send_msgs(self):
        await self.send_json(
            {
                "type": "notify",
                "action": "message.load",
                "content": await self.get_msgs(),
            }
        )

    @database_sync_to_async
    def message_create(self, content):
        msg = self.room.messages.create(contact=self.room.contact, text=content)
        msg.notify_room("create")
        return None
