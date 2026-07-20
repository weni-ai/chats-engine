from typing import Optional
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room

User = get_user_model()


class BulkSendMessagesUseCase:
    """
    Filters active rooms by project (and optionally queues/agents), then
    creates a PENDING ``BulkMessageSend`` record for asynchronous delivery.
    """

    def execute(
        self,
        user_email: str,
        text: str,
        project_uuid: UUID,
        queues: Optional[list[UUID]] = None,
        agents: Optional[list[str]] = None,
    ) -> BulkMessageSend:
        user = User.objects.get(email=user_email)
        project = Project.objects.get(uuid=project_uuid)

        self._get_rooms(project=project, queues=queues, agents=agents)

        bulk_send = BulkMessageSend.objects.create(
            user=user,
            project=project,
            text=text,
            filter_snapshot={
                "queues": [str(queue_uuid) for queue_uuid in (queues or [])],
                "agents": list(agents or []),
            },
            status=BulkMessageSendStatus.PENDING,
        )

        # TODO: Call send bulk messages task

        return bulk_send

    def _get_rooms(
        self,
        project: Project,
        queues: Optional[list[UUID]] = None,
        agents: Optional[list[str]] = None,
    ) -> "QuerySet[Room]":
        rooms = Room.objects.filter(
            is_active=True,
            queue__sector__project=project,
        )

        if queues:
            rooms = rooms.filter(queue__uuid__in=queues)

        if agents:
            rooms = rooms.filter(user__email__in=agents)

        return rooms
