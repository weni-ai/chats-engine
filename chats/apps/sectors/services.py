import logging
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from sentry_sdk import capture_exception


from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.msgs.models import Message, AutomaticMessage
from chats.apps.projects.models.models import Project


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room
    from chats.apps.accounts.models import User


FLOWS_GET_TICKET_RETRIES = settings.AUTOMATIC_MESSAGE_FLOWS_GET_TICKET_RETRIES


class AutomaticMessagesService:
    """
    Service for automatic messages.
    """

    def _get_project_for_ticket(self, room: "Room") -> Project:
        """Get the project to use for ticket verification."""
        secondary_config = room.queue.sector.secondary_project or {}
        secondary_uuid = secondary_config.get("uuid")
        if secondary_uuid:
            return Project.objects.get(uuid=secondary_uuid)
        return room.queue.sector.project

    def _verify_ticket_exists(self, project: Project, ticket_uuid) -> bool:
        """Verify ticket exists with exponential backoff retry."""
        wait_time = 1
        for attempt in range(FLOWS_GET_TICKET_RETRIES + 1):
            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Checking ticket %s (attempt %s)",
                ticket_uuid,
                attempt + 1,
            )
            response = FlowRESTClient().get_ticket(project, ticket_uuid)

            if response.status_code == 200:
                try:
                    results = response.json().get("results", [])
                    if results:
                        logger.info("[AUTOMATIC MESSAGES SERVICE] Ticket %s found", ticket_uuid)
                        return True
                except Exception as e:
                    capture_exception(e)

            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Ticket %s not found. Retrying in %s seconds",
                ticket_uuid,
                wait_time,
            )
            time.sleep(wait_time)
            wait_time *= 2

        return False

    def _should_skip_automatic_message(self, room: "Room") -> bool:
        """Check if automatic message should be skipped."""
        sector = room.queue.sector
        return (
            not sector.is_automatic_message_active
            or not sector.automatic_message_text
            or hasattr(room, "automatic_message")
            or room.messages.filter(user__isnull=False).exists()
        )

    def _create_automatic_message(self, room: "Room", text: str, user: "User") -> bool:
        """Create the automatic message in a transaction."""
        try:
            with transaction.atomic():
                msg = Message.objects.create(room=room, text=text, user=user, contact=None)
                AutomaticMessage.objects.create(room=room, message=msg)
                transaction.on_commit(lambda: msg.notify_room("create", True))
                logger.info("[AUTOMATIC MESSAGES SERVICE] Automatic message sent to room %s", room.pk)
            return True
        except Exception as e:
            logger.error(
                "[AUTOMATIC MESSAGES SERVICE] Error sending automatic message to room %s: %s",
                room.pk,
                e,
                exc_info=True,
            )
            capture_exception(e)
            return False

    def send_automatic_message(
        self, room: "Room", message: str, user: "User", check_ticket: bool = False
    ):
        """Send an automatic message to a room."""
        ticket_uuid = room.ticket_uuid

        if ticket_uuid and check_ticket:
            logger.info("[AUTOMATIC MESSAGES SERVICE] Checking ticket %s", ticket_uuid)
            project = self._get_project_for_ticket(room)
            if not self._verify_ticket_exists(project, ticket_uuid):
                logger.info(
                    "[AUTOMATIC MESSAGES SERVICE] Ticket %s not found after %s attempts",
                    ticket_uuid,
                    FLOWS_GET_TICKET_RETRIES,
                )
                raise Exception(
                    "Automatic Message cannot be send because ticket %s not found for room %s"
                    % (ticket_uuid, room.pk)
                )

        if self._should_skip_automatic_message(room):
            logger.info("[AUTOMATIC MESSAGES SERVICE] Automatic message not sent to room %s", room.pk)
            return False

        return self._create_automatic_message(room, message, user)
