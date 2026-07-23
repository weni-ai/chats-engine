import logging
import traceback

from django.db import transaction

from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    Message,
)
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


class SendBulkMessageToRoomUseCase:
    """
    Creates and delivers a bulk-send message to a single room.

    Attribution follows the room's assigned agent when present; otherwise the
    message is created with no user (system-style).

    Always persists a ``BulkMessageSendMessage`` row with SUCCESS or FAILED.
    Failures are logged at info level and stored in ``errors``; they are not
    sent to Sentry.
    """

    def execute(
        self, bulk_send: BulkMessageSend, room: Room
    ) -> BulkMessageSendMessage:
        logger.info(
            f"[SendBulkMessageToRoomUseCase] Sending bulk message to room with UUID {room.uuid}"
            f"for bulk send with UUID {bulk_send.uuid}"
        )

        if not room.is_active:
            error_message = "Closed rooms can't receive messages"
            logger.info(
                f"[SendBulkMessageToRoomUseCase] Room with UUID {room.uuid} is not active; "
                f"marking bulk send {bulk_send.uuid} as FAILED for this room"
            )
            return BulkMessageSendMessage.objects.create(
                bulk_message_send=bulk_send,
                room=room,
                message=None,
                status=BulkMessageSendMessageStatus.FAILED,
                errors={
                    "error": error_message,
                    "traceback": "",
                },
            )

        try:
            with transaction.atomic():
                message = Message.objects.create(
                    room=room,
                    user=room.user,
                    contact=None,
                    text=bulk_send.text,
                )
                bulk_message = BulkMessageSendMessage.objects.create(
                    bulk_message_send=bulk_send,
                    room=room,
                    message=message,
                    status=BulkMessageSendMessageStatus.SUCCESS,
                )
                room.update_last_message(message=message, user=message.user)
                transaction.on_commit(lambda: message.notify_room("create", True))

                # TODO: Register progress (send an internal event)

                logger.info(
                    f"[SendBulkMessageToRoomUseCase] Sent bulk message to room with UUID {room.uuid}"
                    f"for bulk send with UUID {bulk_send.uuid}"
                )

                return bulk_message
        except Exception as exc:
            logger.info(
                f"[SendBulkMessageToRoomUseCase] Failed to send bulk message to room "
                f"with UUID {room.uuid} for bulk send with UUID {bulk_send.uuid}: {exc}",
                exc_info=True,
            )
            return BulkMessageSendMessage.objects.create(
                bulk_message_send=bulk_send,
                room=room,
                message=None,
                status=BulkMessageSendMessageStatus.FAILED,
                errors={
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
