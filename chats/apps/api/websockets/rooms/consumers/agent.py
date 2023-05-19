import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone

from chats.apps.api.websockets.rooms.validators import WSJoinValidator
from chats.apps.rooms.models import Room


class AgentRoomConsumer(AsyncJsonWebsocketConsumer):
    """
    Agent side of the chat
    """

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
                self.permission = await self.get_permission()
            except ObjectDoesNotExist:
                close = True
            if close:
                await self.close()
            else:
                await self.accept()
                await self.load_queues()
                await self.load_user()
                self.last_ping = timezone.now()

    async def disconnect(self, *args, **kwargs):
        for group in set(self.added_groups):
            try:
                await self.channel_layer.group_discard(group, self.channel_name)
            except AssertionError:
                pass

        if self.permission:
            await self.set_user_status(
                "OFFLINE"
            )  # What if the user has two or more channels connected?

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
            self.last_ping = timezone.now()
            await self.send_json({"type": "pong"})

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

        validator = WSJoinValidator(
            group_name=event["name"],
            group_id=event["id"],
            project_uuid=self.project,
            user_permission=self.permission,
        )
        try:
            if await validator.validate() is False:
                await self.notify(
                    {
                        "type": "notify",
                        "action": "group.join",
                        "content": json.dumps(
                            {"msg": f"Access denied on the group: {group_name}"}
                        ),
                    }
                )
                return None
        except ObjectDoesNotExist:
            await self.notify(
                {
                    "type": "notify",
                    "action": "group.join",
                    "content": json.dumps(
                        {"msg": f"Access denied on the group: {group_name}"}
                    ),
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
        self.permission.status = status
        self.permission.save()
        self.permission.notify_user("update", "system")

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
        await self.join({"name": "permission", "id": str(self.permission.pk)})
