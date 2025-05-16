from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.ai_features.history_summary.services import HistorySummaryService
from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue


class TestHistorySummaryService(TestCase):
    def setUp(self):
        self.mock_integration_client = Mock()
        self.mock_integration_client_class = Mock(
            return_value=self.mock_integration_client
        )
        self.service = HistorySummaryService(self.mock_integration_client_class)

        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="17:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.contact = Contact.objects.create(name="Test Contact")

        # Create test messages
        self.message1 = Message.objects.create(
            room=self.room,
            text="Hello, how can I help you?",
            contact=None,  # Agent message
        )
        self.message2 = Message.objects.create(
            room=self.room, text="I need help with my order", contact=self.contact
        )

        # Create test history summary
        self.history_summary = HistorySummary.objects.create(
            room=self.room, status=HistorySummaryStatus.PENDING
        )

        # Create test feature prompt
        self.feature_prompt = FeaturePrompt.objects.create(
            feature="history_summary",
            version=1,
            model="gpt-4",
            prompt="Please summarize this conversation:\n{conversation}",
            settings={"temperature": 0.7},
        )

    @patch("chats.apps.ai_features.history_summary.services.FeaturePrompt.objects")
    def test_get_prompt(self, mock_feature_prompt_objects):
        # Setup mock
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            self.feature_prompt
        )

        # Test
        result = self.service.get_prompt()

        # Assertions
        self.assertEqual(result, self.feature_prompt)
        mock_feature_prompt_objects.filter.assert_called_once_with(
            feature=self.service.feature_name
        )

    @patch("chats.apps.ai_features.history_summary.services.FeaturePrompt.objects")
    def test_get_prompt_no_prompt_found(self, mock_feature_prompt_objects):
        # Setup mock
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            None
        )

        # Test and Assertions
        with self.assertRaises(ValueError):
            self.service.get_prompt()

    @patch("chats.apps.ai_features.history_summary.services.FeaturePrompt.objects")
    def test_generate_summary_success(self, mock_feature_prompt_objects):
        # Setup mocks
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            self.feature_prompt
        )
        self.mock_integration_client.generate_text.return_value = "Test summary"

        # Test
        result = self.service.generate_summary(self.room, self.history_summary)

        # Assertions
        self.assertEqual(result.status, HistorySummaryStatus.DONE)
        self.assertEqual(result.summary, "Test summary")
        self.mock_integration_client_class.assert_called_once_with("gpt-4")
        self.mock_integration_client.generate_text.assert_called_once()

    @patch("chats.apps.ai_features.history_summary.services.FeaturePrompt.objects")
    def test_generate_summary_invalid_prompt(self, mock_feature_prompt_objects):
        # Setup mocks
        invalid_prompt = FeaturePrompt.objects.create(
            feature="history_summary",
            version=1,
            model="gpt-4",
            prompt="Invalid prompt without conversation placeholder",
            settings={"temperature": 0.7},
        )
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            invalid_prompt
        )

        # Test
        result = self.service.generate_summary(self.room, self.history_summary)

        # Assertions
        self.assertIsNone(result)
        self.assertEqual(self.history_summary.status, HistorySummaryStatus.UNAVAILABLE)
        self.mock_integration_client.generate_text.assert_not_called()
