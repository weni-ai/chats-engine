import json
import asyncio
import uuid
import logging
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from chats.core.cache import CacheClient


USE_WS_CONNECTION_CHECK = getattr(settings, "USE_WS_CONNECTION_CHECK", False)


logger = logging.getLogger(__name__)


class AgentRoomConsumer(AsyncJsonWebsocketConsumer):
    """
    Agent side of the chat
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = CacheClient()

    async def connect(self, *args, **kwargs):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        self.added_groups = []
        self.user = None
        # Are they logged in?
        close = False
        self.permission = None
        self.connection_id = uuid.uuid4()
        self.connection_check_response = False

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
            # Only set status as OFFLINE if there are no other active connections
            logger.info(
                "User %s has been disconnected from connection %s. "
                "Checking if they have other other active connections",
                self.user.email,
                self.connection_id,
            )

            if USE_WS_CONNECTION_CHECK:
                has_other_connections = await self.has_other_active_connections()
                if not has_other_connections:
                    logger.info(
                        "User %s has no other active connections, setting status to OFFLINE",
                        self.user.email,
                    )
                    await self.set_user_status("OFFLINE")
                else:
                    logger.info(
                        "User %s has other active connections, not setting status to OFFLINE",
                        self.user.email,
                    )

            else:
                logger.info(
                    "WS Connection Check is disabled, setting status to OFFLINE",
                    self.user.email,
                )
                await self.set_user_status("OFFLINE")

    async def set_connection_check_response(self, connection_id: str, response: bool):
        self.cache.set(
            f"connection_check_response_{connection_id}", str(response), ex=10
        )

    async def get_connection_check_response(self):
        return self.cache.get(f"connection_check_response_{self.connection_id}")

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
        """Handle notifications including connection checks"""
        if event.get("action") == "connection_check":
            # If this is a connection check message and it's not from our own channel
            logger.info(
                "Connection ID: %s received connection check from %s to check if user %s has other active connections",
                self.connection_id,
                event["content"].get("connection_id"),
                event["content"].get("user_email"),
            )
            if event["content"].get("connection_id") != str(self.connection_id):
                logger.info(
                    "Connection ID: %s sending connection check response to user %s",
                    self.connection_id,
                    event["content"].get("user_email"),
                )
                # Send response through the channel layer
                await self.channel_layer.group_send(
                    f"permission_{self.permission.pk}",
                    {
                        "type": "notify",
                        "action": "connection_check_response",
                        "content": {
                            "connection_id": event["content"].get("connection_id"),
                            "user_email": self.user.email,
                        },
                    },
                )
        elif event.get("action") == "connection_check_response":
            # Handle the response by setting the flag
            logger.info(
                "Connection ID: %s received connection check response from %s to check if user %s has other active connections",
                self.connection_id,
                event["content"].get("connection_id"),
                event["content"].get("user_email"),
            )
            await self.set_connection_check_response(
                connection_id=event["content"].get("connection_id"), response=True
            )
        else:
            await self.send_json(event)

    # SYNC HELPER FUNCTIONS

    @database_sync_to_async
    def set_user_status(self, status: str):
        self.permission.refresh_from_db()
        self.permission.status = status
        self.permission.save(update_fields=["status"])
        self.permission.notify_user("update", "system")

    @database_sync_to_async
    def get_permission(self):
        return self.user.project_permissions.get(project__uuid=self.project)

    @database_sync_to_async
    def get_queues(self, *args, **kwargs):
        """ """
        self.queues = self.permission.queue_ids
        return self.queues

    async def has_other_active_connections(self):
        """
        Check if there are other active connections for this user's permission
        """
        group_name = f"permission_{self.permission.pk}"

        # Send a check message to the group
        await self.channel_layer.group_send(
            group_name,
            {
                "type": "notify",
                "action": "connection_check",
                "content": {"connection_id": str(self.connection_id)},
            },
        )

        logger.info(
            "Connection ID: %s sent connection check to user %s to check if they have other active connections",
            self.connection_id,
            self.user.email,
        )

        # Wait a short time for responses
        await asyncio.sleep(1)

        check_response = bool(await self.get_connection_check_response())

        logger.info(
            "Connection ID: %s got response: %s from user %s to check if they have other active connections",
            self.connection_id,
            check_response,
            self.user.email,
        )

        # If we got a response, there are other active connections
        return check_response

    async def load_queues(self, *args, **kwargs):
        """Enter queue notification groups"""
        queues = await self.get_queues()
        for queue in queues:
            await self.join({"name": "queue", "id": str(queue)})

    async def load_user(self, *args, **kwargs):
        """Enter user notification group"""
        await self.join({"name": "permission", "id": str(self.permission.pk)})
