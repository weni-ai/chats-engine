from celery import shared_task
from django.conf import settings

from chats.apps.msgs.models import ChatMessageReplyIndex
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    UpdateStatusMessageUseCase,
)

update_message_usecase = UpdateStatusMessageUseCase()


@shared_task(
    bind=True,
    max_retries=settings.MESSAGE_STATUS_MAX_RETRIES,
    default_retry_delay=settings.MESSAGE_STATUS_RETRY_DELAY,
)
def process_message_status(self, message_id: str, message_status: str):
    """Task Celery for processing message status with automatic retry"""
    if not ChatMessageReplyIndex.objects.filter(external_id=message_id).exists():
        raise self.retry()

    update_message_usecase.update_status_message(message_id, message_status)
