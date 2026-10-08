from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase

from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageTypeChoices,
)
from chats.apps.ai_features.improve_user_message.usecases import (
    ImproveUserMessageUseCase,
)
from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.projects.models import Project


class ImproveUserMessageUseCaseTests(TestCase):
    def setUp(self):
        cache.clear()
        self.project = Project.objects.create(name="Test Project")
        self.mock_factory = MagicMock()
        self.mock_client_instance = MagicMock()
        self.mock_factory.get_client_class.return_value = MagicMock(
            return_value=self.mock_client_instance
        )
        self.use_case = ImproveUserMessageUseCase(
            integration_client_factory=self.mock_factory
        )

    def test_returns_improved_text(self):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix: {message}",
            settings={"temperature": 0.5},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "hello world"

        result = self.use_case.execute(
            text="hello wrold",
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            project=self.project,
        )

        self.assertEqual(result, "hello world")

    def test_delegates_to_service_with_correct_params(self):
        FeaturePrompt.objects.create(
            feature="clarity",
            model="test-model",
            prompt="Clarify: {message}",
            settings={"temperature": 0.3},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "clear text"

        self.use_case.execute(
            text="unclear text",
            improvement_type=ImprovedUserMessageTypeChoices.CLARITY,
            project=self.project,
        )

        self.mock_factory.get_client_class.assert_called_once_with("bedrock")
        self.mock_client_instance.generate_text.assert_called_once()

    def test_raises_value_error_when_prompt_missing(self):
        with self.assertRaises(ValueError):
            self.use_case.execute(
                text="hello",
                improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
                project=self.project,
            )

    def test_works_for_all_improvement_types(self):
        self.mock_client_instance.generate_text.return_value = "improved"

        for choice in ImprovedUserMessageTypeChoices:
            feature_name = {
                ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING: "grammar_and_spelling",
                ImprovedUserMessageTypeChoices.MORE_EMPATHY: "more_empathy",
                ImprovedUserMessageTypeChoices.CLARITY: "clarity",
            }[choice]

            FeaturePrompt.objects.get_or_create(
                feature=feature_name,
                version=1,
                defaults={
                    "model": "test-model",
                    "prompt": "Improve: {message}",
                    "settings": {"temperature": 0.5},
                },
            )

            result = self.use_case.execute(
                text="some text",
                improvement_type=choice,
                project=self.project,
            )
            self.assertEqual(result, "improved")

    def test_uses_default_factory_when_none_provided(self):
        from chats.apps.ai_features.integrations.factories import (
            AIModelPlatformClientFactory,
        )

        use_case = ImproveUserMessageUseCase()
        self.assertIs(
            use_case.integration_client_factory, AIModelPlatformClientFactory
        )

        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix: {message}",
            settings={"temperature": 0.5},
            version=1,
        )

        with patch.object(
            use_case.integration_client_factory, "get_client_class"
        ) as mock_get_client_class:
            mock_client = MagicMock()
            mock_client.generate_text.return_value = "fixed"
            mock_get_client_class.return_value = MagicMock(return_value=mock_client)

            result = use_case.execute(
                text="broken text",
                improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
                project=self.project,
            )

            self.assertEqual(result, "fixed")
            mock_get_client_class.assert_called_once_with("bedrock")
