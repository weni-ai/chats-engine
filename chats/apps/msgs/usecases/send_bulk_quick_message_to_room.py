import logging
import traceback

from django.db import transaction

from chats.apps.msgs.models import (
    BulkQuickMessageSend,
    BulkQuickMessageSendMessage,
    BulkQuickMessageSendMessageStatus,
    Message,
)
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


class SendBulkQuickMessageToRoomUseCase:
    """
    Creates and delivers a bulk quick-message send to a single room.

    Attribution uses the requesting attendant (``bulk_send.user``). Rooms that
    are closed or no longer assigned to that attendant are recorded as FAILED
    without creating a ``Message``.

    Always persists a ``BulkQuickMessageSendMessage`` row with SUCCESS or FAILED.
    Failures are logged at info level and stored in ``errors``; they are not
    sent to Sentry.
    """

    def execute(
        self, bulk_send: BulkQuickMessageSend, room: Room
    ) -> BulkQuickMessageSendMessage:
        logger.info(
            f"[SendBulkQuickMessageToRoomUseCase] Sending bulk quick message to "
            f"room with UUID {room.uuid} for bulk send with UUID {bulk_send.uuid}"
        )

        if not room.is_active:
            return self._fail(
                bulk_send,
                room,
                "Closed rooms can't receive messages",
                traceback_text="",
            )

        if room.user != bulk_send.user:
            return self._fail(
                bulk_send,
                room,
                "Room is not assigned to the requesting attendant",
                traceback_text="",
            )

        try:
            with transaction.atomic():
                message = Message.objects.create(
                    room=room,
                    user=bulk_send.user,
                    contact=None,
                    text=bulk_send.text,
                )
                bulk_message = BulkQuickMessageSendMessage.objects.create(
                    bulk_quick_message_send=bulk_send,
                    room=room,
                    message=message,
                    status=BulkQuickMessageSendMessageStatus.SUCCESS,
                )
                room.update_last_message(message=message, user=message.user)
                transaction.on_commit(lambda: message.notify_room("create", True))
                # TODO: update bulk quick message send progress

                logger.info(
                    f"[SendBulkQuickMessageToRoomUseCase] Sent bulk quick message "
                    f"to room with UUID {room.uuid} for bulk send with UUID "
                    f"{bulk_send.uuid}"
                )

                return bulk_message
        except Exception as exc:
            logger.info(
                f"[SendBulkQuickMessageToRoomUseCase] Failed to send bulk quick "
                f"message to room with UUID {room.uuid} for bulk send with UUID "
                f"{bulk_send.uuid}: {exc}",
                exc_info=True,
            )
            return self._fail(
                bulk_send,
                room,
                str(exc),
                traceback_text=traceback.format_exc(),
            )

    def _fail(
        self,
        bulk_send: BulkQuickMessageSend,
        room: Room,
        error_message: str,
        traceback_text: str,
    ) -> BulkQuickMessageSendMessage:
        logger.info(
            f"[SendBulkQuickMessageToRoomUseCase] Room with UUID {room.uuid} "
            f"could not receive bulk send {bulk_send.uuid}: {error_message}"
        )
        bulk_message = BulkQuickMessageSendMessage.objects.create(
            bulk_quick_message_send=bulk_send,
            room=room,
            message=None,
            status=BulkQuickMessageSendMessageStatus.FAILED,
            errors={
                "error": error_message,
                "traceback": traceback_text,
            },
        )
        # TODO: update bulk quick message send progress
        return bulk_message
