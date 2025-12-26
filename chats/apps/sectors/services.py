import logging
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from sentry_sdk import capture_exception

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.msgs.models import AutomaticMessage, Message
from chats.apps.projects.models.models import Project

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.accounts.models import User
    from chats.apps.rooms.models import Room


FLOWS_GET_TICKET_RETRIES = settings.AUTOMATIC_MESSAGE_FLOWS_GET_TICKET_RETRIES


class AutomaticMessagesService:
    """
    Service for automatic messages.
    """

    def _get_project_for_ticket_check(self, room: "Room"):
        secondary_project_config = room.queue.sector.secondary_project or {}
        if secondary_project_uuid := secondary_project_config.get("uuid"):
            return Project.objects.get(uuid=secondary_project_uuid)
        return room.queue.sector.project

    def _check_ticket_exists(self, project, ticket_uuid):
        response = FlowRESTClient().get_ticket(project, ticket_uuid)
        if response.status_code != 200:
            return False
        try:
            results = response.json().get("results")
            return len(results) > 0
        except Exception as e:
            capture_exception(e)
            return False

    def _wait_for_ticket(self, room: "Room", ticket_uuid):
        logger.info("[AUTOMATIC MESSAGES SERVICE] Checking ticket %s", ticket_uuid)
        project = self._get_project_for_ticket_check(room)
        wait_time = 1

        for attempt in range(FLOWS_GET_TICKET_RETRIES + 1):
            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Checking ticket %s (attempt %s)",
                ticket_uuid,
                attempt + 1,
            )

            if self._check_ticket_exists(project, ticket_uuid):
                logger.info("[AUTOMATIC MESSAGES SERVICE] Ticket %s found", ticket_uuid)
                return True

            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Ticket %s not found. Retrying in %s seconds",
                ticket_uuid,
                wait_time,
            )
            time.sleep(wait_time)
            wait_time *= 2

        logger.info(
            "[AUTOMATIC MESSAGES SERVICE] Ticket %s not found after %s attempts",
            ticket_uuid,
            FLOWS_GET_TICKET_RETRIES,
        )
        return False

    def _should_send_message(self, room: "Room"):
        sector = room.queue.sector
        if not sector.is_automatic_message_active:
            return False
        if not sector.automatic_message_text:
            return False
        if hasattr(room, "automatic_message"):
            return False
        if room.messages.filter(user__isnull=False).exists():
            return False
        return True

    def _create_automatic_message(self, room: "Room", message_text: str, user: "User"):
        with transaction.atomic():
            message = Message.objects.create(
                room=room,
                text=message_text,
                user=user,
                contact=None,
            )
            AutomaticMessage.objects.create(room=room, message=message)
            transaction.on_commit(lambda: message.notify_room("create", True))
        return message

    def send_automatic_message(
        self, room: "Room", message: str, user: "User", check_ticket: bool = False
    ):
        """
        Send an automatic message to a room.
        """
        ticket_uuid = room.ticket_uuid

        if ticket_uuid and check_ticket:
            if not self._wait_for_ticket(room, ticket_uuid):
                raise Exception(
                    "Automatic Message cannot be send because ticket %s not found for room %s"
                    % (ticket_uuid, room.pk)
                )

        if not self._should_send_message(room):
            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Automatic message not sent to room %s",
                room.pk,
            )
            return False

        try:
            self._create_automatic_message(room, message, user)
            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Automatic message sent to room %s",
                room.pk,
            )
            return True
        except Exception as e:
            logger.error(
                "[AUTOMATIC MESSAGES SERVICE] Error sending automatic message to room %s: %s"
                % (room.pk, e),
                exc_info=True,
            )
            capture_exception(e)
            return False
