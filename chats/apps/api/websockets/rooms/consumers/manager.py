import uuid

from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from chats.apps.api.websockets.rooms.consumers.agent import AgentRoomConsumer


class ManagerAgentRoomConsumer(AgentRoomConsumer):
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
                    self.user = await UserModel.objects.aget(email=user_email)
                    self.permission = await self.get_permission()
                else:
                    close = True
            except ObjectDoesNotExist:
                close = True
            if close:
                await self.close()  # TODO validate if the code continues from this or if it stops here
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

        # Finalizar In-Service se necessário
        await self.finalize_in_service_if_needed()

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
