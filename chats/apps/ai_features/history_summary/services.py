from typing import TYPE_CHECKING
from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.models import FeaturePrompt


if TYPE_CHECKING:
    from django.db.models.query import QuerySet

    from chats.apps.rooms.models import Room
    from chats.apps.msgs.models import Message


class HistorySummaryService:
    """
    Service to generate a summary of the history of a room.
    """

    def __init__(self, integration_client_class: BaseAIPlatformClient):
        self.feature_name = "history_summary"
        self.integration_client_class = integration_client_class

    def get_prompt(self) -> FeaturePrompt:
        """
        Get the prompt for the history summary feature.
        """
        prompt = (
            FeaturePrompt.objects.filter(name=self.feature_name)
            .order_by("version")
            .last()
        )

        if not prompt:
            raise ValueError("No prompt found for the history summary feature")

        return prompt

    def generate_summary(self, room: "Room") -> str:
        """
        Generate a summary of the history of a room.
        """
        feature_prompt = self.get_prompt()

        model_id = feature_prompt.model
        prompt_text = feature_prompt.prompt

        if "{conversation}" not in prompt_text:
            raise ValueError("Prompt text needs to have a {conversation} placeholder")

        messages: QuerySet["Message"] = room.messages.all()

        conversation_text = ""

        for message in messages:
            is_contact = message.contact is not None
            sender = "contact" if is_contact else "agent"

            conversation_text += f"<{sender}>: {message.text}\n"

        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt_text}],
                }
            ],
        }

        for setting, value in feature_prompt.settings.items():
            request_body[setting] = value

        summary = self.integration_client_class(model_id).generate_text(request_body)

        return summary
