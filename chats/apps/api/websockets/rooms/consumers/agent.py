import json
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from chats.apps.api.websockets.rooms.cache import CacheClient
from chats.apps.projects.models.models import ProjectPermission


CONNECTION_CACHE_TTL = 60  # 1 minute


class AgentRoomConsumer(AsyncJsonWebsocketConsumer):
    """
    Agent side of the chat
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_client = CacheClient()

    async def connect(self, *args, **kwargs):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        self.added_groups = []
        self.user = None
        # Are they logged in?
        close = False
        self.permission = None

        try:
            self.user = self.scope["user"]
            self.project = self.scope["query_params"].get("project")[0]
        except (KeyError, TypeError):
            close = True
        if self.user.is_anonymous or close is True or self.project is None:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            try:
                self.permission: ProjectPermission = await self.get_permission()
            except ObjectDoesNotExist:
                close = True
            if close:
                await self.close()
            else:
                await self.accept()
                await self.load_queues()
                await self.load_user()

                # Register the connection
                await self.register_connection()

                self.last_ping = timezone.now()

    async def disconnect(self, *args, **kwargs):
        for group in set(self.added_groups):
            try:
                await self.channel_layer.group_discard(group, self.channel_name)
            except AssertionError:
                pass

        # Unregister the connection
        await self.unregister_connection()

        conn_count = await self.get_connections_count()

        if conn_count == 0:
            if self.permission:
                await self.set_user_status("OFFLINE")

    async def get_cache_pattern(self):
        return "agent_room_connection:%s:%s"

    async def get_connection_id(self):
        if not (connection_id := getattr(self, "connection_id", None)):
            connection_id = str(uuid.uuid4())

            setattr(self, "connection_id", connection_id)

        return connection_id

    async def get_cache_key(self):
        return await self.get_cache_pattern() % (
            self.permission.pk,
            await self.get_connection_id(),
        )

    async def register_connection(self):
        cache_key = await self.get_cache_key()

        self.cache_client.set(
            cache_key,
            self.channel_name,
            ex=CONNECTION_CACHE_TTL,
        )

        await self.update_last_seen()

        return cache_key

    async def unregister_connection(self):
        cache_key = await self.get_cache_key()
        self.cache_client.delete(cache_key)

    async def get_connections_count(self):
        cache_key = await self.get_cache_pattern() % (self.permission.pk, "*")
        return len(self.cache_client.get_list(cache_key))

    async def receive_json(self, payload):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on

        command_name = payload.get("type", None)
        if command_name == "notify":
            await self.notify(payload["content"])
        elif command_name == "method":
            command = getattr(self, payload["action"])
            await command(payload["content"])
        elif command_name == "ping":
            # Renew the connection cache
            await self.register_connection()

            self.last_ping = timezone.now()
            await self.send_json(
                {
                    "type": "pong",
                }
            )

    # METHODS

    async def exit(self, event):
        """
        Exit group by event
        """
        if event.get("content"):
            event = json.loads(event.get("content"))

        group_name = f"{event['name']}_{event['id']}"
        try:
            self.added_groups.remove(group_name)
            await self.channel_layer.group_discard(group_name, self.channel_name)
        except (ValueError, AssertionError):
            pass
        if settings.DEBUG:
            # for debugging
            await self.notify(
                {
                    "type": "notify",
                    "action": "group.exit",
                    "content": json.dumps(
                        {"msg": f"Exited {group_name} to your listening groups"}
                    ),
                }
            )

    async def list_groups(self, event):
        await self.notify(
            {
                "type": "notify",
                "action": "groups",
                "content": {"groups": self.added_groups},
            }
        )

    async def join(self, event):
        if event.get("content"):
            event = json.loads(event.get("content"))
        group_name = f"{event['name']}_{event['id']}"

        if event.get("name") not in ["permission", "queue"]:
            await self.notify(
                {
                    "type": "notify",
                    "action": "group.join",
                    "content": json.dumps({"msg": f"Group {group_name} is deprecated"}),
                }
            )
            return None

        await self.channel_layer.group_add(group_name, self.channel_name)
        self.added_groups.append(group_name)

        if settings.DEBUG:
            await self.notify(
                {
                    "type": "notify",
                    "action": "group.join",
                    "content": json.dumps(
                        {"msg": f"Added {group_name} to your listening groups"}
                    ),
                }
            )

    # SUBSCRIPTIONS
    async def notify(self, event):
        """ """
        await self.send_json(event)

    # SYNC HELPER FUNCTIONS

    @database_sync_to_async
    def set_user_status(self, status: str):
        self.permission.refresh_from_db()
        self.permission.status = status
        self.permission.save(update_fields=["status"])
        self.permission.notify_user("update", "system")

    @database_sync_to_async
    def update_last_seen(self):
        self.permission.last_seen_online = timezone.now()
        self.permission.save(update_fields=["last_seen_online"])

    @database_sync_to_async
    def get_permission(self) -> ProjectPermission:
        return self.user.project_permissions.get(project__uuid=self.project)

    @database_sync_to_async
    def get_queues(self, *args, **kwargs):
        """ """
        self.queues = self.permission.queue_ids
        return self.queues

    async def load_queues(self, *args, **kwargs):
        """Enter queue notification groups"""
        queues = await self.get_queues()
        for queue in queues:
            await self.join({"name": "queue", "id": str(queue)})

    async def load_user(self, *args, **kwargs):
        """Enter user notification group"""
        await self.join({"name": "permission", "id": str(self.permission.pk)})
