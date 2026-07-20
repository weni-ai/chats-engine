from uuid import UUID

from celery import shared_task
from django.conf import settings

from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendStatus,
    ChatMessageReplyIndex,
)
from chats.apps.msgs.usecases.get_bulk_send_rooms import GetBulkSendRoomsUseCase
from chats.apps.msgs.usecases.send_bulk_message_to_room import (
    SendBulkMessageToRoomUseCase,
)
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    UpdateStatusMessageUseCase,
)
from chats.apps.rooms.models import Room

update_message_usecase = UpdateStatusMessageUseCase()
get_bulk_send_rooms_usecase = GetBulkSendRoomsUseCase()
send_bulk_message_to_room_usecase = SendBulkMessageToRoomUseCase()


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
    bulk_send = BulkMessageSend.objects.get(uuid=bulk_send_uuid)
    bulk_send.status = BulkMessageSendStatus.PROCESSING
    bulk_send.save(update_fields=["status", "modified_on"])

    rooms = get_bulk_send_rooms_usecase.execute(bulk_send)
    for room_uuid in rooms.values_list("uuid", flat=True):
        send_bulk_message_to_room.delay(bulk_send_uuid, room_uuid)


@shared_task
def send_bulk_message_to_room(bulk_send_uuid: UUID, room_uuid: UUID):
    """
    Send the bulk message text to a single room.
    """
    bulk_send = BulkMessageSend.objects.get(uuid=bulk_send_uuid)
    room = Room.objects.get(uuid=room_uuid)
    send_bulk_message_to_room_usecase.execute(bulk_send, room)
