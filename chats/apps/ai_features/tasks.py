from uuid import UUID
from chats.celery import app
import logging

from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.ai_features.history_summary.services import HistorySummaryService
from chats.apps.ai_features.integrations.factories import AIModelPlatformClientFactory
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


@app.task
def generate_history_summary(room_uuid: UUID):
    room = Room.objects.get(uuid=room_uuid)

    history_summary = HistorySummary.objects.create(
        room=room,
        status=HistorySummaryStatus.PENDING,
    )

    # For now, we only support Bedrock
    # That's why is hardcoded here
    # This might change in the future
    integration_client_class = AIModelPlatformClientFactory.get_client_class("bedrock")
    history_summary_service = HistorySummaryService(integration_client_class)

    history_summary_service.generate_summary(room, history_summary)
