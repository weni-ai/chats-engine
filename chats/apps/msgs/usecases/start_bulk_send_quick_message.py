import logging

from typing import List, Optional
from uuid import UUID

from django.contrib.auth import get_user_model

from chats.apps.msgs.models import BulkQuickMessageSend, BulkQuickMessageSendStatus
from chats.apps.msgs.tasks import process_bulk_quick_message_send
from chats.apps.projects.models import Project

User = get_user_model()

logger = logging.getLogger(__name__)


class StartBulkSendQuickMessageUseCase:
    """
    Creates a PENDING ``BulkQuickMessageSend`` record for asynchronous delivery.

    ``contacts`` is stored as ``None`` when the send targets all ongoing rooms
    of the requesting attendant in the project. A list of contact UUIDs
    (including an empty list) is stored as UUID strings. Room filtering and
    message delivery are handled by a later async task.
    """

    def execute(
        self,
        user_email: str,
        text: str,
        project_uuid: UUID,
        contacts: Optional[List[UUID]] = None,
    ) -> BulkQuickMessageSend:
        logger.info(
            f"[StartBulkSendQuickMessageUseCase] Starting bulk quick message send "
            f"for user {user_email} in project {project_uuid} "
            f"with contacts {contacts}"
        )

        user = User.objects.get(email=user_email)
        project = Project.objects.get(uuid=project_uuid)

        stored_contacts = (
            None
            if contacts is None
            else [str(contact_uuid) for contact_uuid in contacts]
        )

        bulk_send = BulkQuickMessageSend.objects.create(
            user=user,
            project=project,
            text=text,
            contacts=stored_contacts,
            status=BulkQuickMessageSendStatus.PENDING,
        )

        logger.info(
            f"[StartBulkSendQuickMessageUseCase] Created bulk quick message send "
            f"with UUID {bulk_send.uuid} with status {bulk_send.status}"
        )

        process_bulk_quick_message_send.delay(bulk_send.uuid)

        return bulk_send
