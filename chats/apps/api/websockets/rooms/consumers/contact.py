import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ContactRoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.contact = None
        self.room = self.scope["url_route"]["kwargs"]["room_id"]

        self.room_group_name = f"room_{self.room}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, payload):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "notify", "message": payload["content"]}
        )

    async def notify(self, event):
        await self.send_json(json.dumps(event["content"]))

    async def method(self, *args, **kwargs):
        pass
