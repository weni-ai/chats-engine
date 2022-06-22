import json

from django.db.models import Q

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from chats.apps.rooms.models import Room


# todo: ADD TRY EXCEPTS


class AgentRoomConsumer(AsyncJsonWebsocketConsumer):
    """
    Agent side of the chat
    """

    rooms = []
    sectors = []
    user = []

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

        await self.agent_load_rooms()
        await self.agent_load_queues()
        await self.agent_notification_room()

    async def disconnect(self, *args, **kwargs):
        for room in self.rooms:
            await self.channel_layer.group_discard(f"room_{room}", self.channel_name)
            await self.channel_layer.group_discard(
                f"room_notify_{room}", self.channel_name
            )
        for sector in self.sectors:
            await self.channel_layer.group_discard(
                f"sector_{sector}", self.channel_name
            )
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
        command = getattr(self, command_name)
        await command(payload["content"])

    # INITIALIZE GROUPS
    async def agent_load_rooms(self, *args, **kwargs):
        """Enter room notification groups"""
        self.rooms = await self.get_user_rooms()
        for room in self.rooms:
            await self._add_to_group("room", room)

    async def agent_load_queues(self, *args, **kwargs):
        """Enter queue notification groups"""
        sector_queues = await self.get_sectors()
        for sector in sector_queues:
            await self._add_to_group("sector", sector)

    async def agent_notification_room(self, *args, **kwargs):
        """Enter user notification group"""
        await self._add_to_group("user", self.user.pk)

    # GROUP MANAGEMENT

    async def agent_join_room(self, user, room, type, *args, **kwargs):
        """ """
        await self._add_to_group("room", room)

    async def agent_exit_room(self, user, room, type, *args, **kwargs):
        """ """
        await self.channel_layer.group_discard(f"room_{room}", self.channel_name)

    # SUBSCRIPTIONS
    async def room_messages(self, event):
        """ """
        await self.send_json(
            text_data=json.dumps({"type": "room_messages", "content": event})
        )

    async def room_changed(self, event):
        """ """
        await self.send_json(
            text_data=json.dumps({"type": "room_changed", "content": event})
        )

    async def sector_changed(self, event):
        """ """
        await self.send_json(
            text_data=json.dumps({"type": "new_room", "content": event})
        )

    async def join_room(self, event):
        """ """
        room_pk = event["room"]
        await self._add_to_group("room", room_pk)

    async def join_sector(self, event):
        """ """
        room_pk = event["room"]
        await self._add_to_group("room", room_pk)

    # SYNC HELPER FUNCTIONS

    async def _add_to_group(self, group_name, id):
        """Just so we don't need to write this big guy"""
        await self.channel_layer.group_add(f"{group_name}_{id}", self.channel_name)

    @database_sync_to_async
    def get_user_rooms(self, user, *args, **kwargs):
        """ """
        rooms = Room.objects.filter(Q(user=user) | Q(user__isnull=True), is_active=True)
        return list(rooms.values_list("pk", flat=True))

    def get_valid_room(self, room, *args, **kwargs):
        """ """
        room = Room.objects.get(pk=room, user=self.user)
        return room

    def get_sectors(self, *args, **kwargs):
        """ """
        self.sectors = self.user.sector_permissions.all().values_list(
            "sector__pk", flat=True
        )
        return self.sectors
