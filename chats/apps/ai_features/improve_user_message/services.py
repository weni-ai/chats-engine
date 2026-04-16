from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageTypeChoices,
    ImprovedUserMessageStatusChoices,
)
from chats.apps.ai_features.improve_user_message.models import (
    MessageImprovementStatus,
)
from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.integrations.dataclass import PromptMessage
from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.feature_flags.exceptions import FeatureFlagInactiveError
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project

if TYPE_CHECKING:
    from typing import Type


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
        user_message_text: str,
        improvement_type: ImprovedUserMessageTypeChoices,
        project: Project,
    ) -> str:
        raise NotImplementedError


class ImproveUserMessageService(BaseImproveUserMessageService):
    """
    Service for improving user messages.
    """

    def __init__(self, integration_client_class: "Type[BaseAIPlatformClient]"):
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

    def _get_improvement_feature_prompt_config(
        self, improvement_type: ImprovedUserMessageTypeChoices
    ) -> FeaturePrompt:
        """
        Get the improvement feature prompt config.
        """
        if improvement_type not in FEATURE_PROMPT_IMPROVEMENT_TYPE_MAPPING:
            raise ValueError(f"Invalid improvement type: {improvement_type}")

        feature_name = FEATURE_PROMPT_IMPROVEMENT_TYPE_MAPPING[improvement_type]
        cache_key = f"ai_features:improve_user_message:{feature_name}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        feature_prompt = (
            FeaturePrompt.objects.filter(feature=feature_name)
            .order_by("version")
            .last()
        )

        if not feature_prompt:
            raise ValueError(
                f"No feature prompt found for improvement type: {improvement_type}"
            )

        cache.set(
            cache_key,
            feature_prompt,
            settings.IMPROVE_USER_MESSAGE_FEATURE_PROMPT_CACHE_TTL,
        )

        return feature_prompt

    def generate_improved_message(
        self,
        user_message_text: str,
        improvement_type: ImprovedUserMessageTypeChoices,
        project: Project,
    ) -> str:
        """
        Generate an improved message.
        """
        if not is_feature_active_for_attributes(
            settings.IMPROVE_USER_MESSAGE_FEATURE_FLAG_KEY,
            {"projectUUID": str(project.uuid)},
        ):
            raise FeatureFlagInactiveError(
                "Feature flag is not active for this project"
            )

        feature_prompt_config = self._get_improvement_feature_prompt_config(
            improvement_type
        )
        model_id = feature_prompt_config.model
        prompt_text = feature_prompt_config.prompt

        message_placeholder_count = prompt_text.count("{message}")
        if message_placeholder_count == 0:
            raise ValueError("Prompt text needs to have a {message} placeholder")
        if message_placeholder_count > 1:
            raise ValueError("Prompt text must have exactly one {message} placeholder")

        prefix, suffix = prompt_text.split("{message}")

        prompt_msgs = [
            PromptMessage(text=prefix, should_cache=True),
            PromptMessage(text=user_message_text, should_cache=False),
        ]

        if suffix:
            prompt_msgs.append(PromptMessage(text=suffix, should_cache=True))

        improved_message_text = self.integration_client_class(model_id).generate_text(
            feature_prompt_config.settings, prompt_msgs
        )

        return improved_message_text
