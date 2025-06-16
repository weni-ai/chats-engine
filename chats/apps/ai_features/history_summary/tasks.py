from uuid import UUID
from chats.celery import app
import logging

from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.ai_features.history_summary.services import HistorySummaryService
from chats.apps.ai_features.integrations.factories import AIModelPlatformClientFactory

logger = logging.getLogger(__name__)


@app.task
def generate_history_summary(history_summary_uuid: UUID):
    """
    Generate a history summary for a room.
    """
    history_summary = HistorySummary.objects.get(uuid=history_summary_uuid)
    room = history_summary.room

    # For now, we only support Bedrock
    # That's why is hardcoded here
    # This might change in the future
    integration_client_class = AIModelPlatformClientFactory.get_client_class("bedrock")
    history_summary_service = HistorySummaryService(integration_client_class)

    history_summary_service.generate_summary(room, history_summary)


@app.task
def cancel_history_summary_generation(history_summary_uuid: UUID):
    """
    Cancel a history summary generation if no summary
    is generated for it after some time.
    """
    history_summary = HistorySummary.objects.get(uuid=history_summary_uuid)
    if history_summary.status == HistorySummaryStatus.PENDING:
        history_summary.status = HistorySummaryStatus.UNAVAILABLE
        history_summary.save()
