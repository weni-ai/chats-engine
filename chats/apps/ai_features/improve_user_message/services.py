from abc import ABC, abstractmethod
import logging


from chats.apps.msgs.models import Message
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageTypeChoices,
    ImprovedUserMessageStatusChoices,
)
from chats.apps.ai_features.improve_user_message.models import (
    MessageImprovementStatus,
)


logger = logging.getLogger(__name__)


class BaseImproveUserMessageService(ABC):
    """
    Base service for improving user messages.
    """

    @abstractmethod
    def register_message_improvement(
        self,
        message: Message,
        improvement_type: ImprovedUserMessageTypeChoices,
        status: ImprovedUserMessageStatusChoices,
    ):
        raise NotImplementedError


class ImproveUserMessageService(BaseImproveUserMessageService):
    """
    Service for improving user messages.
    """

    def register_message_improvement(
        self,
        message: Message,
        improvement_type: ImprovedUserMessageTypeChoices,
        status: ImprovedUserMessageStatusChoices,
    ):
        """
        Register a message improvement.
        """
        if MessageImprovementStatus.objects.filter(message=message).exists():
            logger.warning(
                "Message improvement already registered for message %s",
                message.uuid,
            )
            return

        MessageImprovementStatus.objects.create(
            message=message,
            type=improvement_type,
            status=status,
        )
