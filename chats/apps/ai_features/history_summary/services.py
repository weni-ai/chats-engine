import json
import logging
from typing import TYPE_CHECKING

from django.db.models import Q
from sentry_sdk import capture_message
from chats.apps.ai_features.history_summary.models import HistorySummaryStatus
from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.models import FeaturePrompt


if TYPE_CHECKING:
    from django.db.models.query import QuerySet

    from chats.apps.rooms.models import Room
    from chats.apps.msgs.models import Message
    from chats.apps.ai_features.history_summary.models import HistorySummary


logger = logging.getLogger(__name__)


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
            FeaturePrompt.objects.filter(feature=self.feature_name)
            .order_by("version")
            .last()
        )

        if not prompt:
            raise ValueError("No prompt found for the history summary feature")

        return prompt

    def generate_summary(
        self, room: "Room", history_summary: "HistorySummary"
    ) -> "HistorySummary":
        """
        Generate a summary of the history of a room.
        """
        feature_prompt = self.get_prompt()

        model_id = feature_prompt.model
        prompt_text = feature_prompt.prompt

        if "{conversation}" not in prompt_text:
            history_summary.update_status(HistorySummaryStatus.UNAVAILABLE)
            logger.error(
                "History summary prompt text needs to have a {conversation} placeholder. Room: %s",
                room.uuid,
            )
            capture_message(
                "History summary prompt text needs to have a {conversation} placeholder. Room: %s"
                % room.uuid,
                level="error",
            )
            return None

        history_summary.update_status(HistorySummaryStatus.PROCESSING)

        try:
            messages: QuerySet["Message"] = room.messages.filter(
                Q(user__isnull=False) | Q(contact__isnull=False)
            ).select_related("contact", "user")

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

            summary_text = self.integration_client_class(model_id).generate_text(
                feature_prompt.settings, prompt_text
            )

            logger.info(
                "Response from AI for room %s: %s",
                room.uuid,
                summary_text,
            )

            if "<no_summary_available>" in summary_text:
                history_summary.update_status(HistorySummaryStatus.UNAVAILABLE)
                reason = summary_text.replace("<no_summary_available>", "").replace(
                    "</no_summary_available>", ""
                )
                logger.info(
                    "A summary could not be generated for room %s. The reason provided by the AI was: %s",
                    room.uuid,
                    reason,
                )
            else:
                history_summary.summary = summary_text
                history_summary.update_status(HistorySummaryStatus.DONE)

            history_summary.feature_prompt = feature_prompt
            history_summary.save()

        except Exception as e:
            history_summary.update_status(HistorySummaryStatus.UNAVAILABLE)
            logger.error(
                "Error generating history summary for room %s: %s", room.uuid, e
            )
            capture_message(
                "Error generating history summary for room %s: %s" % (room.uuid, e),
                level="error",
            )

        return history_summary
