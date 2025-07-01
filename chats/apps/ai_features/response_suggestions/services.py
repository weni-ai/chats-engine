from typing import TYPE_CHECKING
from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.models import FeaturePrompt


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room


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

    def get_response_suggestion(self, room: "Room") -> str:
        """
        Get the response suggestion for the copilot feature.
        """
        feature_prompt = self.get_prompt()

        model_id = feature_prompt.model
        prompt_text = feature_prompt.prompt

        # TODO: Inject the conversation inside the prompt

        messages = Room.objects.get(id=room.id).messages.order_by("created_at")
