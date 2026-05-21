from unittest.mock import patch

from django.test import TestCase

from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.ai_features.history_summary.tasks import (
    cancel_history_summary_generation,
    generate_history_summary,
)
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class _BaseHistorySummaryTaskTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="HS Test Project")
        self.sector = Sector.objects.create(
            name="HS Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="HS Queue", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.history_summary = HistorySummary.objects.create(
            room=self.room, status=HistorySummaryStatus.PENDING
        )


class TestGenerateHistorySummary(_BaseHistorySummaryTaskTestCase):
    @patch(
        "chats.apps.ai_features.history_summary.tasks.AIModelPlatformClientFactory"
    )
    @patch("chats.apps.ai_features.history_summary.tasks.HistorySummaryService")
    def test_invokes_service_with_bedrock_client(
        self, mock_service_class, mock_factory
    ):
        client_class = object()
        mock_factory.get_client_class.return_value = client_class

        generate_history_summary(self.history_summary.uuid)

        mock_factory.get_client_class.assert_called_once_with("bedrock")
        mock_service_class.assert_called_once_with(client_class)
        mock_service_class.return_value.generate_summary.assert_called_once_with(
            self.room, self.history_summary
        )


class TestCancelHistorySummaryGeneration(_BaseHistorySummaryTaskTestCase):
    def test_marks_pending_as_unavailable(self):
        cancel_history_summary_generation(self.history_summary.uuid)

        self.history_summary.refresh_from_db()
        self.assertEqual(
            self.history_summary.status, HistorySummaryStatus.UNAVAILABLE
        )

    def test_leaves_non_pending_alone(self):
        self.history_summary.status = HistorySummaryStatus.DONE
        self.history_summary.save()

        cancel_history_summary_generation(self.history_summary.uuid)

        self.history_summary.refresh_from_db()
        self.assertEqual(self.history_summary.status, HistorySummaryStatus.DONE)
