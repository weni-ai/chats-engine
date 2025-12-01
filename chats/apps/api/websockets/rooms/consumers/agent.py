import asyncio
import json
import logging
import time
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from chats.apps.api.v1.prometheus.metrics import (
    ws_active_connections,
    ws_connection_duration,
    ws_connections_total,
    ws_disconnects_total,
    ws_messages_received_total,
)
from chats.apps.history.filters.rooms_filter import (
    get_history_rooms_queryset_by_contact,
)
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.projects.usecases.status_service import InServiceStatusService
from chats.apps.rooms.models import Room
from chats.core.cache import CacheClient

logger = logging.getLogger(__name__)

USE_WS_CONNECTION_CHECK = getattr(settings, "USE_WS_CONNECTION_CHECK", False)
CONNECTION_CHECK_CACHE_PREFIX = "connection_check_response_"
CONNECTION_CHECK_WAIT_TIME = 1
CONNECTION_CHECK_TIMEOUT = 1
CONNECTION_CHECK_CACHE_TTL = 10

# Ping timeout configuration
PING_TIMEOUT_SECONDS = getattr(settings, "WS_PING_TIMEOUT_SECONDS", 60)
PING_CHECK_INTERVAL_SECONDS = getattr(settings, "WS_PING_CHECK_INTERVAL_SECONDS", 10)

logger = logging.getLogger(__name__)


class AgentRoomConsumer(AsyncJsonWebsocketConsumer):
    CONSUMER_TYPE = "agent"
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
        self._start_time = time.time()
        try:
            ws_connections_total.labels(consumer=self.CONSUMER_TYPE).inc()
            ws_active_connections.labels(consumer=self.CONSUMER_TYPE).inc()
        except Exception as e:
            logger.warning(f"Error updating Prometheus metrics: {e}")

        self.added_groups = []
        self.user = None
        # Are they logged in?
        close = False
        self.permission = None
        self.connection_id = uuid.uuid4()

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
                
                # Start background task to monitor ping timeout
                self.ping_timeout_task = asyncio.create_task(self.ping_timeout_checker())

    async def disconnect(self, *args, **kwargs):
        # Cancel the ping timeout checker task
        if hasattr(self, 'ping_timeout_task') and not self.ping_timeout_task.done():
            self.ping_timeout_task.cancel()
            try:
                await self.ping_timeout_task
            except asyncio.CancelledError:
                logger.debug(f"ping_timeout_task cancelled for user {self.user.email if self.user else 'unknown'}")
        
        try:
            ws_active_connections.labels(consumer=self.CONSUMER_TYPE).dec()
            ws_disconnects_total.labels(consumer=self.CONSUMER_TYPE).inc()
            if hasattr(self, "_start_time"):
                ws_connection_duration.labels(consumer=self.CONSUMER_TYPE).observe(
                    time.time() - self._start_time
                )
        except Exception as e:
            logger.warning(f"Error updating Prometheus metrics: {e}")

        for group in set(self.added_groups):
            try:
                await self.channel_layer.group_discard(group, self.channel_name)
            except AssertionError:
                pass

        if self.permission:
            if USE_WS_CONNECTION_CHECK:
                # Only set status as OFFLINE if there are no other active connections
                logger.info(
                    "User %s has been disconnected from connection %s. "
                    "Checking if they have other other active connections",
                    self.user.email,
                    self.connection_id,
                )

                has_other_connections = await self.has_other_active_connections()
                if not has_other_connections:
                    logger.info(
                        "User %s has no other active connections, setting status to OFFLINE",
                        self.user.email,
                    )
                    await self.set_user_status("OFFLINE")
                    await self.finalize_in_service_if_needed()
                    # await self.log_status_change("OFFLINE")
                else:
                    logger.info(
                        "User %s has other active connections, not setting status to OFFLINE",
                        self.user.email,
                    )

            else:
                logger.info(
                    "WS Connection Check is disabled, setting %s status to OFFLINE",
                    self.user.email,
                )
                await self.set_user_status("OFFLINE")
                await self.finalize_in_service_if_needed()
                # await self.log_status_change("OFFLINE")

    async def set_connection_check_response(self, connection_id: str, response: bool):
        self.cache.set(
            f"{CONNECTION_CHECK_CACHE_PREFIX}{connection_id}",
            str(response),
            ex=CONNECTION_CHECK_CACHE_TTL,
        )

    async def get_connection_check_response(self):
        key = f"{CONNECTION_CHECK_CACHE_PREFIX}{self.connection_id}"
        response = self.cache.get(key)

        if response is not None:
            self.cache.delete(key)

        return response

    async def receive_json(self, payload):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        ws_messages_received_total.labels(consumer=self.CONSUMER_TYPE).inc()

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
            if (
                event["content"].get("connection_id") != str(self.connection_id)
                and event["content"].get("user_email") == self.user.email
            ):
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
                "Connection ID: %s received connection check response "
                "from %s to check if user %s has other active connections",
                self.connection_id,
                event["content"].get("connection_id"),
                event["content"].get("user_email"),
            )
            await self.set_connection_check_response(
                connection_id=event["content"].get("connection_id"), response=True
            )
        elif "rooms." in event.get("action"):
            content = event.get("content", {})

            try:
                if isinstance(content, str):
                    content = json.loads(content)

                room_uuid = content.get("uuid")

                if not room_uuid:
                    return self.send_json(event)

                has_history = await self.get_has_history_by_room_uuid(room_uuid)
                content["has_history"] = has_history

                event["content"] = json.dumps(
                    content,
                    sort_keys=True,
                    indent=1,
                    cls=DjangoJSONEncoder,
                )
            except Exception as e:
                logger.error(f"Error getting history rooms queryset by contact: {e}")
                return self.send_json(event)

            await self.send_json(event)
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

    @database_sync_to_async
    def get_has_history_by_room_uuid(self, room_uuid: str):
        room = Room.objects.get(uuid=room_uuid)
        return get_history_rooms_queryset_by_contact(
            room.contact, self.user, room.queue.sector.project
        ).exists()

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
                "content": {
                    "connection_id": str(self.connection_id),
                    "user_email": self.user.email,
                },
            },
        )

        logger.info(
            "Connection ID: %s sent connection check to user %s to check if they have other active connections",
            self.connection_id,
            self.user.email,
        )

        # Wait a short time for responses
        await asyncio.sleep(CONNECTION_CHECK_WAIT_TIME)

        # Wait a short time for responses
        try:
            check_response = await asyncio.wait_for(
                self.get_connection_check_response(),
                timeout=CONNECTION_CHECK_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Connection check timed out for user %s", self.user.email)

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

    @database_sync_to_async
    def finalize_in_service_if_needed(self):
        try:
            permission = ProjectPermission.objects.get(
                user=self.user, project_id=self.project
            )
            if permission.status == ProjectPermission.STATUS_ONLINE:
                InServiceStatusService.room_closed(self.user, permission.project)
        except ProjectPermission.DoesNotExist:
            pass

    async def ping_timeout_checker(self):
        """
        Background task that monitors ping activity.
        If no ping is received for PING_TIMEOUT_SECONDS, sets user offline and closes connection.
        """
        try:
            while True:
                # Check every PING_CHECK_INTERVAL_SECONDS
                await asyncio.sleep(PING_CHECK_INTERVAL_SECONDS)
                
                # Safety check: stop if permission is gone
                if not hasattr(self, 'permission') or self.permission is None:
                    logger.info("ping_timeout_checker: permission gone, stopping task")
                    break
                
                # Skip if last_ping not set yet
                if not hasattr(self, 'last_ping'):
                    continue
                
                # Calculate time since last ping
                seconds_since_ping = (timezone.now() - self.last_ping).total_seconds()
                
                # Check if timeout threshold exceeded
                if seconds_since_ping > PING_TIMEOUT_SECONDS:
                    logger.warning(
                        f"Ping timeout detected for user {self.user.email} "
                        f"(project: {self.project}). "
                        f"Last ping was {seconds_since_ping:.0f} seconds ago "
                        f"(threshold: {PING_TIMEOUT_SECONDS}s). "
                        f"Setting status to OFFLINE and closing connection."
                    )
                    
                    # Set user status to OFFLINE
                    await self.set_user_status("OFFLINE")
                    
                    # Finalize any in-service status
                    await self.finalize_in_service_if_needed()
                    
                    # Close the WebSocket connection
                    await self.close(code=1000)
                    
                    # Exit the loop
                    break
                    
        except asyncio.CancelledError:
            # Task was cancelled (normal during disconnect)
            logger.debug(
                f"ping_timeout_checker cancelled for user "
                f"{self.user.email if hasattr(self, 'user') and self.user else 'unknown'}"
            )
            raise
        except Exception as e:
            # Unexpected error - log and stop task
            logger.error(
                f"Unexpected error in ping_timeout_checker for user "
                f"{self.user.email if hasattr(self, 'user') and self.user else 'unknown'}: {e}",
                exc_info=True
            )

    # async def log_status_change(
    #     self,
    #     status: str,
    #     custom_status_name: str = None,
    #     custom_status_type_uuid: str = None,
    # ):
    #     """Log agent status change via Celery task"""
    #     from chats.apps.projects.tasks import log_agent_status_change

    #     log_agent_status_change.delay(
    #         agent_email=self.user.email,
    #         project_uuid=str(self.permission.project.uuid),
    #         status=status,
    #         custom_status_name=custom_status_name,
    #         custom_status_type_uuid=custom_status_type_uuid,
    #     )
