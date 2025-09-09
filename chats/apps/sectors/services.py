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

    def should_send_automatic_message(self, room: Room) -> bool:
        """
        Check if the automatic message should be sent to a room.
        """
        return (
            room.queue.sector.is_automatic_message_active
            and room.automatic_message is None
            and not room.messages.filter(user__isnull=False).exists()
        )

    def send_automatic_message(self, room: Room, message: str, user: User):
        """
        Send an automatic message to a room.
        """
        if not self.should_send_automatic_message(room):
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
            logger.error("Error sending automatic message to room %s: %s", room.pk, e)
            capture_exception(e)
            return
