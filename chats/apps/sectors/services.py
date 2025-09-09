import logging

from django.db import transaction

from chats.apps.rooms.models import Room
from chats.apps.msgs.models import Message, AutomaticMessage


logger = logging.getLogger(__name__)


class AutomaticMessagesService:
    """
    Service for automatic messages.
    """

    def send_automatic_message(self, room: Room, message: str, user: User):
        """
        Send an automatic message to a room.
        """
        if room.automatic_message:
            logger.error("Automatic message already exists for room %s", room.pk)
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
            return
