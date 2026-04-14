import logging

from chats.celery import app
from chats.apps.msgs.models import Message
from chats.apps.ai_features.improve_user_message.services import (
    ImproveUserMessageService,
)


logger = logging.getLogger(__name__)


@app.task
def register_message_improvement_task(
    message_uuid: str,
    improvement_type: str,
    status: str,
):
    """
    Register a message improvement.
    """
    logger.info(
        "[register_message_improvement_task] Starting task to register message improvement for message %s with type %s and status %s",
        message_uuid,
        improvement_type,
        status,
    )
    try:
        message = Message.objects.get(uuid=message_uuid)
    except Message.DoesNotExist:
        logger.error(
            "[register_message_improvement_task] Message not found for UUID %s",
            message_uuid,
        )
        return

    service = ImproveUserMessageService()
    service.register_message_improvement(
        message=message,
        improvement_type=improvement_type,
        status=status,
    )
    logger.info(
        "[register_message_improvement_task] Message improvement registered for message %s with type %s and status %s",
        message_uuid,
        improvement_type,
        status,
    )
