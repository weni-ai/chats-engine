from datetime import timedelta
from uuid import UUID
import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendStatus,
    ChatMessageReplyIndex,
)
from chats.apps.msgs.usecases.get_bulk_send_rooms import GetBulkSendRoomsUseCase
from chats.apps.msgs.usecases.send_bulk_message_to_room import (
    SendBulkMessageToRoomUseCase,
)
from chats.apps.msgs.usecases.update_bulk_message_send_progress import (
    UpdateBulkMessageSendProgressUseCase,
)
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    UpdateStatusMessageUseCase,
)
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)

update_message_usecase = UpdateStatusMessageUseCase()
get_bulk_send_rooms_usecase = GetBulkSendRoomsUseCase()
send_bulk_message_to_room_usecase = SendBulkMessageToRoomUseCase()
update_bulk_message_send_progress_usecase = UpdateBulkMessageSendProgressUseCase()


def get_bulk_send_progress_lock_key(bulk_send_uuid: UUID) -> str:
    return f"bulk_send_progress_lock:{bulk_send_uuid}"


def get_bulk_send_progress_pending_key(bulk_send_uuid: UUID) -> str:
    return f"bulk_send_progress_pending:{bulk_send_uuid}"


@shared_task(
    bind=True,
    max_retries=settings.MESSAGE_STATUS_MAX_RETRIES,
    default_retry_delay=settings.MESSAGE_STATUS_RETRY_DELAY,
)
def process_message_status(self, message_id: str, message_status: str):
    """Task Celery for processing message status with automatic retry"""
    print(f"[TASK] Iniciando: {message_id} - {message_status}")

    if not ChatMessageReplyIndex.objects.filter(external_id=message_id).exists():
        if self.request.retries >= settings.MESSAGE_STATUS_MAX_RETRIES - 1:
            print(f"[WARNING] Message without external_id: {message_id}")
            return
        raise self.retry()

    update_message_usecase.update_status_message(message_id, message_status)


@shared_task
def process_bulk_message_send(bulk_send_uuid: UUID):
    """
    Mark a bulk send as PROCESSING and fan out one send task per matching room.
    """
    logger.info(
        f"[process_bulk_message_send] Processing bulk send with UUID {bulk_send_uuid}"
    )

    bulk_send = BulkMessageSend.objects.get(uuid=bulk_send_uuid)
    rooms = get_bulk_send_rooms_usecase.execute(bulk_send)
    room_uuids = list(rooms.values_list("uuid", flat=True))

    bulk_send.status = BulkMessageSendStatus.PROCESSING
    bulk_send.rooms_qty = len(room_uuids)
    bulk_send.save(update_fields=["status", "rooms_qty", "modified_on"])

    logger.info(
        f"[process_bulk_message_send] Bulk send with UUID {bulk_send_uuid} "
        f"marked as PROCESSING"
    )

    for room_uuid in room_uuids:
        send_bulk_message_to_room.delay(bulk_send_uuid, room_uuid)

    logger.info(
        f"[process_bulk_message_send] Dispatched send bulk message to room tasks "
        f"for bulk send with UUID {bulk_send_uuid}"
    )


@shared_task
def send_bulk_message_to_room(bulk_send_uuid: UUID, room_uuid: UUID):
    """
    Send the bulk message text to a single room.
    """
    logger.info(
        f"[send_bulk_message_to_room] Sending bulk message to room with UUID {room_uuid}"
    )

    bulk_send = BulkMessageSend.objects.get(uuid=bulk_send_uuid)
    room = Room.objects.get(uuid=room_uuid)
    send_bulk_message_to_room_usecase.execute(bulk_send, room)

    logger.info(
        f"[send_bulk_message_to_room] Sent bulk message to room with UUID {room_uuid}"
    )


@shared_task
def update_bulk_message_send_progress(bulk_send_uuid: UUID):
    """
    Update bulk send progress with a 1/sec cooldown.

    When the cooldown lock is held, schedules at most one deferred retry so the
    latest progress (including 100%) is still delivered after the window.
    """
    lock_key = get_bulk_send_progress_lock_key(bulk_send_uuid)
    pending_key = get_bulk_send_progress_pending_key(bulk_send_uuid)

    acquired = cache.add(
        lock_key, True, timeout=settings.BULK_SEND_PROGRESS_COOLDOWN_SECONDS
    )
    if not acquired:
        logger.info(
            "[update_bulk_message_send_progress] Progress cooldown is active for "
            "bulk send %s. Skipping update for now.",
            bulk_send_uuid,
        )
        already_pending = not cache.add(
            pending_key, True, timeout=settings.BULK_SEND_PROGRESS_RETRY_DELAY
        )
        if not already_pending:
            update_bulk_message_send_progress.apply_async(
                args=[bulk_send_uuid],
                countdown=settings.BULK_SEND_PROGRESS_RETRY_DELAY,
            )
            logger.info(
                "[update_bulk_message_send_progress] Scheduled deferred progress "
                "update for bulk send %s",
                bulk_send_uuid,
            )
        return False

    update_bulk_message_send_progress_usecase.execute(bulk_send_uuid)
    # Do not delete the lock — TTL enforces the 1 update/sec rate limit.
    return True


@shared_task(name="finish_stale_bulk_message_sends")
def finish_stale_bulk_message_sends():
    """
    Mark bulk sends older than BULK_SEND_STALE_FINISH_MINUTES as FINISHED.

    Preventive measure so bulk sends are closed even if progress tracking fails.
    """
    cutoff = timezone.now() - timedelta(
        minutes=settings.BULK_SEND_STALE_FINISH_MINUTES
    )
    updated = (
        BulkMessageSend.objects.filter(created_on__lte=cutoff)
        .exclude(status=BulkMessageSendStatus.FINISHED)
        .update(status=BulkMessageSendStatus.FINISHED, modified_on=timezone.now())
    )
    logger.info(
        "[finish_stale_bulk_message_sends] Marked %s stale bulk sends as FINISHED",
        updated,
    )
    return updated
