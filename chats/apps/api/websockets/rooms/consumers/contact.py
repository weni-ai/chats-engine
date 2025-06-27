import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from chats.apps.api.v1.msgs.serializers import MessageWSSerializer
from chats.apps.api.v1.prometheus.metrics import (
    ws_active_connections,
    ws_connection_duration,
    ws_connections_total,
    ws_disconnects_total,
    ws_messages_received_total,
)
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


class ContactRoomConsumer(AsyncJsonWebsocketConsumer):
    CONSUMER_TYPE = "contact"

    async def connect(self):
        self._start_time = time.time()
        try:
            ws_connections_total.labels(consumer=self.CONSUMER_TYPE).inc()
            ws_active_connections.labels(consumer=self.CONSUMER_TYPE).inc()
        except Exception as e:
            logger.warning(f"Error updating Prometheus metrics: {e}")

        self.room_id = self.scope["url_route"]["kwargs"]["room"]
        self.order_by = self.scope["query_params"].get("order_by", ["-created_at"])[
            0
        ]  # default ordering

        self.room_group_name = f"room_{self.room_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.get_room()

        await self.accept()

        await self.send_msgs()

    async def disconnect(self, close_code):
        try:
            ws_active_connections.labels(consumer=self.CONSUMER_TYPE).dec()
            ws_disconnects_total.labels(consumer=self.CONSUMER_TYPE).inc()
            if hasattr(self, "_start_time"):
                ws_connection_duration.labels(consumer=self.CONSUMER_TYPE).observe(
                    time.time() - self._start_time
                )
        except Exception as e:
            logger.warning(f"Error updating Prometheus metrics: {e}")

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, payload):
        ws_messages_received_total.labels(consumer=self.CONSUMER_TYPE).inc()

        command_name = payload.get("type")
        if command_name == "notify":
            await self.notify(payload["content"])
        elif command_name == "method":
            action = payload.get("action")
            content = payload.get("content")
            if hasattr(self, action):
                command = getattr(self, action)
                await command(content)
            else:
                # Optional: handle unknown action
                pass

    async def notify(self, event):
        # event["content"] is expected to be a dict/JSON-compatible object
        await self.send_json(event["content"])

    @database_sync_to_async
    def get_room(self):
        self.room = Room.objects.get(pk=self.room_id)
        self.contact = self.room.contact

    @database_sync_to_async
    def get_msgs(self):
        msgs = self.room.messages.all().order_by(self.order_by)
        return MessageWSSerializer(msgs, many=True).data

    async def send_msgs(self):
        messages = await self.get_msgs()
        await self.send_json(
            {
                "type": "notify",
                "action": "message.load",
                "content": messages,
            }
        )

    @database_sync_to_async
    def message_create(self, content):
        text = content.get("text") if isinstance(content, dict) else str(content)
        msg = self.room.messages.create(contact=self.contact, text=text)
        msg.notify_room("create")
