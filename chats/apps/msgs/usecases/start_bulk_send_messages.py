import logging

from typing import List, Optional
from uuid import UUID

from django.contrib.auth import get_user_model

from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.msgs.tasks import process_bulk_message_send
from chats.apps.projects.models import Project

User = get_user_model()

logger = logging.getLogger(__name__)


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
        logger.info(
            f"[StartBulkSendMessagesUseCase] Starting bulk send messages "
            f"for user {user_email} in project {project_uuid} "
            f"with queues {queues} and agents {agents}"
        )
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

        logger.info(
            f"[StartBulkSendMessagesUseCase] Created bulk send messages with UUID {bulk_send.uuid}"
            f"with status {bulk_send.status}"
        )

        process_bulk_message_send.delay(bulk_send.uuid)

        return bulk_send
