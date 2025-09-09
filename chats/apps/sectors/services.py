import logging


from chats.apps.rooms.models import Room
from chats.apps.msgs.models import Message


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
            # TODO: Add transaction around this
            message = Message.objects.create(
                room=room,
                text=message,
                user=user,
                contact=None,
            )
        except Exception as e:
            logger.error("Error sending automatic message to room %s: %s", room.pk, e)
            return
