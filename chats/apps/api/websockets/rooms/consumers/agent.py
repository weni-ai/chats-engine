import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q

from chats.apps.rooms.models import Room

# todo: ADD TRY EXCEPTS


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
        self.user = self.scope["user"]
        self.project = self.scope["query_params"].get("project")[0]
        if self.user.is_anonymous or self.project is None:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            await self.accept()
            await self.load_rooms()
            await self.load_user()

    async def disconnect(self, *args, **kwargs):
        for group in set(self.groups):
            await self.channel_layer.group_discard(group, self.channel_name)
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
        # for debugging
        await self.notify(
            {
                "type": "notify",
                "action": "group_exit",
                "content": {"msg": f"Exited {group_name} to your listening groups"},
            }
        )

    async def join(self, event):
        """
        Add group by event(dictionary) or group_name
        """
        group_name = f"{event['name']}_{event['id']}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.groups.append(group_name)
        # for debugging
        await self.notify(
            {
                "type": "notify",
                "action": "group_join",
                "content": {"msg": f"Added {group_name} to your listening groups"},
            }
        )

    # SUBSCRIPTIONS
    async def notify(self, event):
        """ """
        await self.send_json(json.dumps(event))

    # SYNC HELPER FUNCTIONS

    @database_sync_to_async
    def get_user_rooms(self, *args, **kwargs):
        """ """
        permission = self.user.project_permissions.get(project__uuid=self.project)
        queue_ids = permission.queue_ids
        rooms = Room.objects.filter(
            Q(user=self.user) | Q(user__isnull=True),
            queue__uuid__in=queue_ids,
            is_active=True,
        )

        return list(rooms.values_list("pk", flat=True))

    @database_sync_to_async
    def get_sectors(self, *args, **kwargs):
        """ """
        self.sectors = list(self.user.sector_ids)
        return self.sectors

    async def load_rooms(self, *args, **kwargs):
        """Enter room notification groups"""
        self.rooms = await self.get_user_rooms()
        for room in self.rooms:
            await self.join({"name": "room", "id": room})

    async def load_sectors(self, *args, **kwargs):
        """Enter queue notification groups"""
        sector_queues = await self.get_sectors()
        for sector in sector_queues:
            await self.join({"name": "sector", "id": sector})

    async def load_user(self, *args, **kwargs):
        """Enter user notification group"""
        await self.join({"name": "user", "id": self.user.pk})
