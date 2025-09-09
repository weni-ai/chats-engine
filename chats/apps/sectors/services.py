import logging

from django.db import transaction
from sentry_sdk import capture_exception

from chats.apps.rooms.models import Room
from chats.apps.msgs.models import Message, AutomaticMessage
from chats.apps.accounts.models import User


logger = logging.getLogger(__name__)


class AutomaticMessagesService:
    """
    Service for automatic messages.
    """

    def send_automatic_message(self, room: Room, message: str, user: User):
        """
        Send an automatic message to a room.
        """
        if (
            room.queue.sector.is_automatic_message_active
            and room.automatic_message is None
            and not room.messages.filter(user__isnull=False).exists()
        ):
            logger.info(
                "[AUTOMATIC MESSAGES SERVICE] Automatic message not sent to room %s",
                room.pk,
            )
            return

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

                message.notify_room("create", True)
        except Exception as e:
            logger.error(
                "[AUTOMATIC MESSAGES SERVICE] Error sending automatic message to room %s: %s"
                % (room.pk, e),
                exc_info=True,
            )
            capture_exception(e)
            return
