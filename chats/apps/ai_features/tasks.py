from uuid import UUID
from chats.celery import app
import logging

from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
)
from chats.apps.ai_features.history_summary.services import HistorySummaryService
from chats.apps.ai_features.integrations.factories import AIModelPlatformClientFactory

logger = logging.getLogger(__name__)


@app.task
def generate_history_summary(history_summary_uuid: UUID):
    history_summary = HistorySummary.objects.get(uuid=history_summary_uuid)
    room = history_summary.room

    # For now, we only support Bedrock
    # That's why is hardcoded here
    # This might change in the future
    integration_client_class = AIModelPlatformClientFactory.get_client_class("bedrock")
    history_summary_service = HistorySummaryService(integration_client_class)

    history_summary_service.generate_summary(room, history_summary)
