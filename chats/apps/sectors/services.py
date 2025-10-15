import logging
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from sentry_sdk import capture_exception


from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.msgs.models import Message, AutomaticMessage


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room
    from chats.apps.accounts.models import User


FLOWS_GET_TICKET_RETRIES = settings.AUTOMATIC_MESSAGE_FLOWS_GET_TICKET_RETRIES


class AutomaticMessagesService:
    """
    Service for automatic messages.
    """

    def send_automatic_message(
        self, room: "Room", message: str, user: "User", check_ticket: bool = False
    ):
        """
        Send an automatic message to a room.
        """

        ticket_uuid = room.ticket_uuid

        ticket_found = False

        if ticket_uuid and check_ticket:
            logger.info("[AUTOMATIC MESSAGES SERVICE] Checking ticket %s", ticket_uuid)
            wait_time = 1

            for i in range(FLOWS_GET_TICKET_RETRIES):
                logger.info(
                    "[AUTOMATIC MESSAGES SERVICE] Checking ticket %s (attempt %s)",
                    ticket_uuid,
                    i + 1,
                )
                response = FlowRESTClient().get_ticket(
                    room.queue.sector.project, ticket_uuid
                )

                if response.status_code == 200:
                    try:
                        results = response.json().get("results")
                    except Exception as e:
                        capture_exception(e)
                    else:
                        if len(results) > 0:
                            logger.info(
                                "[AUTOMATIC MESSAGES SERVICE] Ticket %s found",
                                ticket_uuid,
                            )
                            ticket_found = True
                            break

                logger.info(
                    "[AUTOMATIC MESSAGES SERVICE] Ticket %s not found. Retrying in %s seconds",
                    ticket_uuid,
                    wait_time,
                )

                time.sleep(wait_time)
                wait_time *= 2

            if not ticket_found:
                logger.info(
                    "[AUTOMATIC MESSAGES SERVICE] Ticket %s not found after %s attempts",
                    ticket_uuid,
                    FLOWS_GET_TICKET_RETRIES,
                )
                raise Exception(
                    "Automatic Message cannot be send because ticket %s not found for room %s"
                    % (ticket_uuid, room.pk)
                )

        if (
            room.queue.sector.is_automatic_message_active is False
            or not room.queue.sector.automatic_message_text
            or hasattr(room, "automatic_message")
            or room.messages.filter(user__isnull=False).exists()
        ):
            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Automatic message not sent to room %s",
                room.pk,
            )
            return False

        try:
            with transaction.atomic():
                message = Message.objects.create(
                    room=room,
                    text=message,
                    user=user,
                    contact=None,
                )
                AutomaticMessage.objects.create(
                    room=room,
                    message=message,
                )

                transaction.on_commit(lambda: message.notify_room("create", True))

                logger.info(
                    "[AUTOMATIC MESSAGES SERVICE] Automatic message sent to room %s",
                    room.pk,
                )
        except Exception as e:
            logger.error(
                "[AUTOMATIC MESSAGES SERVICE] Error sending automatic message to room %s: %s"
                % (room.pk, e),
                exc_info=True,
            )
            capture_exception(e)
            return False

        return True
