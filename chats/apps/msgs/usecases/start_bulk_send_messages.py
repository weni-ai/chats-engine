from typing import List, Optional
from uuid import UUID

from django.contrib.auth import get_user_model

from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.projects.models import Project

User = get_user_model()


class StartBulkSendMessagesUseCase:
    """
    Creates a PENDING ``BulkMessageSend`` record for asynchronous delivery.

    Room filtering and message delivery are handled by a later async task.
    """

    def execute(
        self,
        user_email: str,
        text: str,
        project_uuid: UUID,
        queues: Optional[List[UUID]] = None,
        agents: Optional[List[str]] = None,
    ) -> BulkMessageSend:
        user = User.objects.get(email=user_email)
        project = Project.objects.get(uuid=project_uuid)

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
