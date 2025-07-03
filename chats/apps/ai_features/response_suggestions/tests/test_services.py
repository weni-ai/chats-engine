from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.ai_features.response_suggestions.services import (
    ResponseSuggestionsService,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue


class TestResponseSuggestionsService(TestCase):
    def setUp(self):
        self.mock_integration_client = Mock()
        self.mock_integration_client_class = Mock(
            return_value=self.mock_integration_client
        )
        self.service = ResponseSuggestionsService(self.mock_integration_client_class)

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

        # Create test feature prompt
        self.feature_prompt = FeaturePrompt.objects.create(
            feature="response_suggestions",
            version=1,
            model="gpt-4",
            prompt="Please suggest a response for the following conversation:\n{conversation}",
            settings={"temperature": 0.7},
        )

    @patch("chats.apps.ai_features.response_suggestions.services.FeaturePrompt.objects")
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

    @patch("chats.apps.ai_features.response_suggestions.services.FeaturePrompt.objects")
    def test_get_prompt_no_prompt_found(self, mock_feature_prompt_objects):
        # Setup mock
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            None
        )

        # Test and Assertions
        with self.assertRaises(ValueError):
            self.service.get_prompt()

    @patch("chats.apps.ai_features.response_suggestions.services.FeaturePrompt.objects")
    def test_generate_response_suggestion_success(self, mock_feature_prompt_objects):
        # Setup mocks
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            self.feature_prompt
        )
        self.mock_integration_client.generate_text.return_value = (
            "Test response suggestion"
        )

        # Test
        result = self.service.get_response_suggestion(self.room)

        # Assertions
        self.assertEqual(result, "Test response suggestion")
        self.mock_integration_client_class.assert_called_once_with("gpt-4")
        self.mock_integration_client.generate_text.assert_called_once()

    @patch("chats.apps.ai_features.response_suggestions.services.FeaturePrompt.objects")
    def test_generate_response_suggestion_invalid_prompt(
        self, mock_feature_prompt_objects
    ):
        # Setup mocks
        invalid_prompt = FeaturePrompt.objects.create(
            feature="response_suggestions",
            version=1,
            model="gpt-4",
            prompt="Invalid prompt without conversation placeholder",
            settings={"temperature": 0.7},
        )
        mock_feature_prompt_objects.filter.return_value.order_by.return_value.last.return_value = (
            invalid_prompt
        )

        # Test
        result = self.service.get_response_suggestion(self.room)

        # Assertions
        self.assertIsNone(result)
        self.mock_integration_client.generate_text.assert_not_called()
