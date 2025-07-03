import json
from typing import TYPE_CHECKING
import logging

from django.conf import settings
from sentry_sdk import capture_message

from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.models import FeaturePrompt

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room


# Number of messages to consider for the response suggestion
# It will get the last CHATS_RESPONSE_SUGGESTIONS_MAX_MESSAGES messages from the room
CHATS_RESPONSE_SUGGESTIONS_MAX_MESSAGES = (
    settings.CHATS_RESPONSE_SUGGESTIONS_MAX_MESSAGES
)


class ResponseSuggestionsService:
    """
    Service for the response suggestions features.
    """

    def __init__(self, integration_client_class: BaseAIPlatformClient):
        self.feature_name = "response_suggestions"
        self.integration_client_class = integration_client_class

    def get_prompt(self) -> FeaturePrompt:
        """
        Get the prompt for the copilot features.
        """
        prompt = (
            FeaturePrompt.objects.filter(feature=self.feature_name)
            .order_by("version")
            .last()
        )

        if not prompt:
            raise ValueError("No prompt found for the response suggestions feature")

        return prompt

    def get_response_suggestion(self, room: "Room") -> str | None:
        """
        Get the response suggestion for the copilot feature.
        """
        feature_prompt = self.get_prompt()

        model_id = feature_prompt.model
        prompt_text = feature_prompt.prompt

        if "{conversation}" not in prompt_text:
            logger.error(
                "The prompt does not contain the {conversation} placeholder. Room %s",
                room.id,
            )
            capture_message(
                "The prompt does not contain the {conversation} placeholder. Room %s",
                room.id,
            )
            return None

        messages = (
            Room.objects.get(id=room.id)
            .messages.filter(Q(user__isnull=False) | Q(contact__isnull=False))
            .select_related("contact", "user")
            .order_by("created_at")
        )
        messages_qty = messages.count()

        if messages_qty == 0:
            logger.info("No messages found in the room. Room %s", room.id)
            return None

        try:
            messages = messages[
                messages_qty - CHATS_RESPONSE_SUGGESTIONS_MAX_MESSAGES :
            ]

            conversation = []

            for message in messages:
                is_contact = message.contact is not None
                sender = "user" if is_contact else "agent"

                conversation.append(
                    {
                        "sender": sender,
                        "text": message.text,
                    }
                )

            conversation_text = json.dumps(conversation, ensure_ascii=False)
            prompt_text = prompt_text.format(conversation=conversation_text)

            response = self.integration_client_class(model_id).generate_text(
                feature_prompt.settings, prompt_text
            )

            return response

        except Exception as e:
            logger.error("Error generating response for room %s: %s", room.uuid, e)
            capture_message(
                f"Error generating response for room {room.uuid}: {e}",
                level="error",
            )
