from abc import ABC, abstractmethod
import logging


from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.integrations.dataclass import PromptMessage
from chats.apps.msgs.models import Message
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageTypeChoices,
    ImprovedUserMessageStatusChoices,
)
from chats.apps.ai_features.improve_user_message.models import (
    MessageImprovementStatus,
)
from chats.apps.ai_features.models import FeaturePrompt


logger = logging.getLogger(__name__)


FEATURE_PROMPT_IMPROVEMENT_TYPE_MAPPING = {
    ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING: "grammar_and_spelling",
    ImprovedUserMessageTypeChoices.MORE_EMPATHY: "more_empathy",
    ImprovedUserMessageTypeChoices.CLARITY: "clarity",
}


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

    @abstractmethod
    def generate_improved_message(
        self,
        text: str,
        improvement_type: ImprovedUserMessageTypeChoices,
    ) -> str:
        raise NotImplementedError


class ImproveUserMessageService(BaseImproveUserMessageService):
    """
    Service for improving user messages.
    """

    def __init__(self, integration_client_class: BaseAIPlatformClient):
        self.integration_client_class = integration_client_class

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

    def get_improvement_feature_prompt_config(
        self, improvement_type: ImprovedUserMessageTypeChoices
    ) -> str:
        """
        Get the improvement feature prompt config.
        """
        if improvement_type not in FEATURE_PROMPT_IMPROVEMENT_TYPE_MAPPING:
            raise ValueError(f"Invalid improvement type: {improvement_type}")

        feature_name = FEATURE_PROMPT_IMPROVEMENT_TYPE_MAPPING[improvement_type]

        feature_prompt = (
            FeaturePrompt.objects.filter(feature=feature_name)
            .order_by("version")
            .last()
        )

        if not feature_prompt:
            raise ValueError(
                f"No feature prompt found for improvement type: {improvement_type}"
            )

        return feature_prompt

    def generate_improved_message(
        self,
        user_message_text: str,
        improvement_type: ImprovedUserMessageTypeChoices,
    ) -> str:
        """
        Generate an improved message.
        """
        feature_prompt_config = self.get_improvement_feature_prompt_config(
            improvement_type
        )
        model_id = feature_prompt_config.model
        prompt_text = feature_prompt_config.prompt

        if "{message}" not in prompt_text:
            raise ValueError("Prompt text needs to have a {message} placeholder")

        prompt_initial_context = prompt_text.split("{message}")[0]

        prompt_msgs = [
            PromptMessage(text=prompt_initial_context, should_cache=True),
            PromptMessage(text=user_message_text, should_cache=False),
        ]

        improved_message_text = self.integration_client_class(model_id).generate_text(
            feature_prompt_config.settings, prompt_msgs
        )

        return improved_message_text
