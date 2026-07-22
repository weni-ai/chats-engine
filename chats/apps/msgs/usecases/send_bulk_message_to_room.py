import logging

from django.db import transaction

from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendMessage, Message
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


class SendBulkMessageToRoomUseCase:
    """
    Creates and delivers a bulk-send message to a single room.

    Attribution follows the room's assigned agent when present; otherwise the
    message is created with no user (system-style).
    """

    def execute(self, bulk_send: BulkMessageSend, room: Room) -> Message:
        logger.info(
            f"[SendBulkMessageToRoomUseCase] Sending bulk message to room with UUID {room.uuid}"
            f"for bulk send with UUID {bulk_send.uuid}"
        )

        with transaction.atomic():
            message = Message.objects.create(
                room=room,
                user=room.user,
                contact=None,
                text=bulk_send.text,
            )
            BulkMessageSendMessage.objects.create(
                bulk_message_send=bulk_send,
                message=message,
            )
            room.update_last_message(message=message, user=message.user)
            transaction.on_commit(lambda: message.notify_room("create", True))

            # TODO: Register progress (send an internal event)

            logger.info(
                f"[SendBulkMessageToRoomUseCase] Sent bulk message to room with UUID {room.uuid}"
                f"for bulk send with UUID {bulk_send.uuid}"
            )

            return message
