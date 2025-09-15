import logging
import time
import uuid

from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from chats.apps.api.v1.prometheus.metrics import (
    ws_active_connections,
    ws_connection_duration,
    ws_connections_total,
    ws_disconnects_total,
)
from chats.apps.api.websockets.rooms.consumers.agent import AgentRoomConsumer
from chats.core.cache_utils import get_user_id_by_email_cached

logger = logging.getLogger(__name__)


class ManagerAgentRoomConsumer(AgentRoomConsumer):
    CONSUMER_TYPE = "manager_agent"
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
        self.connection_id = uuid.uuid4()
        UserModel = None
        self._start_time = time.time()

        try:
            self.user = self.scope["user"]
            UserModel = self.user._meta.model

            self.project = self.scope["query_params"].get("project")[0]
        except (KeyError, TypeError, AttributeError):
            close = True

        if self.user.is_anonymous or close is True or self.project is None:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            try:
                self.permission = await self.get_permission()

                user_email = self.scope["query_params"].get("user_email")[0]
                is_manager = await self.check_is_manager()
                if user_email and UserModel and is_manager:
                    self.user = await self._get_user_by_email(UserModel, user_email)
                    self.permission = await self.get_permission()
                else:
                    close = True
            except ObjectDoesNotExist:
                close = True
            if close:
                await self.close()  # TODO validate if the code continues from this or if it stops here
            else:
                await self.accept()
                try:
                    ws_connections_total.labels(consumer=self.CONSUMER_TYPE).inc()
                    ws_active_connections.labels(consumer=self.CONSUMER_TYPE).inc()
                except Exception as e:
                    logger.warning(f"Error updating Prometheus metrics: {e}")
                await self.load_queues()
                await self.load_user()
                self.last_ping = timezone.now()

    async def disconnect(self, *args, **kwargs):
        try:
            ws_active_connections.labels(consumer=self.CONSUMER_TYPE).dec()
            ws_disconnects_total.labels(consumer=self.CONSUMER_TYPE).inc()
            if hasattr(self, "_start_time"):
                ws_connection_duration.labels(consumer=self.CONSUMER_TYPE).observe(
                    time.time() - self._start_time
                )
        except Exception as e:
            logger.warning(f"Error updating Prometheus metrics: {e}")
        await super().disconnect(*args, **kwargs)

    @database_sync_to_async
    def finalize_in_service_if_needed(self):
        from chats.apps.projects.models.models import ProjectPermission
        from chats.apps.projects.usecases.status_service import InServiceStatusService

        try:
            permission = ProjectPermission.objects.get(
                user=self.user, project_id=self.project
            )
            if permission.status == ProjectPermission.STATUS_ONLINE:
                InServiceStatusService.room_closed(self.user, permission.project)
        except ProjectPermission.DoesNotExist:
            pass

    @database_sync_to_async
    def check_is_manager(self):
        return self.permission.is_manager(any_sector=True)

    @database_sync_to_async
    def _get_user_by_email(self, UserModel, user_email: str):
        """
        Resolve user via cache first; fall back to DB by pk.
        Raises UserModel.DoesNotExist on miss (caught by ObjectDoesNotExist).
        """
        email_l = (user_email or "").lower()
        uid = get_user_id_by_email_cached(email_l)
        if uid is None:
            raise UserModel.DoesNotExist
        return UserModel.objects.get(pk=uid)
