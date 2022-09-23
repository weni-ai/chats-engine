from builtins import KeyError, TypeError
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.db.models import Q

from chats.apps.rooms.models import Room


class AgentRoomConsumer(AsyncJsonWebsocketConsumer):
    """
    Agent side of the chat
    """

    groups = []
    user = None

    async def connect(self, *args, **kwargs):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        # Are they logged in?
        try:
            self.user = self.scope["user"]
            self.project = self.scope["query_params"].get("project")[0]
        except (KeyError, TypeError):
            await self.close()
        if self.user.is_anonymous or self.project is None:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            self.permission = await self.get_permission()
            await self.accept()
            await self.load_rooms()
            await self.load_user()
            await self.set_user_status("online")

    async def disconnect(self, *args, **kwargs):
        for group in set(self.groups):
            await self.channel_layer.group_discard(group, self.channel_name)
        await self.set_user_status(
            "offline"
        )  # What if the user has two or more channels connected?
        await self.channel_layer.group_discard(
            f"user_{self.user.pk}", self.channel_name
        )

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

    # METHODS

    async def exit(self, event):
        """
        Exit group by event
        """
        group_name = f"{event['name']}_{event['id']}"
        await self.channel_layer.group_discard(group_name, self.channel_name)
        self.groups.remove(group_name)
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

    async def join(self, event):
        """
        Add group by event(dictionary) or group_name
        """
        # TODO TEST IF A EXTERNAL USER CAN JOIN GROUPS HE DOES NOT HAVE PERMISSION ON e.g: user x joins user y group

        group_name = f"{event['name']}_{event['id']}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.groups.append(group_name)
        # for debugging
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
        self.permission.status = status
        self.permission.save()

    @database_sync_to_async
    def get_permission(self):
        return self.user.project_permissions.get(project__uuid=self.project)

    @database_sync_to_async
    def get_user_rooms(self, *args, **kwargs):
        """ """
        # TODO Think in a new way to query this
        queue_ids = self.permission.queue_ids
        rooms = Room.objects.filter(
            Q(user=self.user) | Q(user__isnull=True),
            queue__uuid__in=queue_ids,
            is_active=True,
        ).values_list("pk", flat=True)

        return list(rooms)

    @database_sync_to_async
    def get_queues(self, *args, **kwargs):
        """ """
        self.queues = self.permission.queue_ids
        return self.queues

    async def load_rooms(self, *args, **kwargs):
        """Enter room notification groups"""
        self.rooms = await self.get_user_rooms()
        for room in self.rooms:

            await self.join({"name": "room", "id": str(room)})

    async def load_queues(self, *args, **kwargs):
        """Enter queue notification groups"""
        queues = await self.get_queues()
        for queue in queues:

            await self.join({"name": "queue", "id": str(queue)})

    async def load_user(self, *args, **kwargs):
        """Enter user notification group"""
        await self.join(
            {"name": "user", "id": self.user.id}
        )  # Group name must be a valid unicode string containing only ASCII alphanumerics, hyphens, or periods.
