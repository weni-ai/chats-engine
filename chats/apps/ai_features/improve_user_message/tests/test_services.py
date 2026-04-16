from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageStatusChoices,
    ImprovedUserMessageTypeChoices,
)
from chats.apps.ai_features.improve_user_message.models import (
    MessageImprovementStatus,
)
from chats.apps.ai_features.improve_user_message.services import (
    ImproveUserMessageService,
)
from chats.apps.ai_features.integrations.dataclass import PromptMessage
from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.contacts.models import Contact
from chats.apps.feature_flags.exceptions import FeatureFlagInactiveError
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class ImproveUserMessageServiceTests(TestCase):
    def setUp(self):
        self.mock_client_class = MagicMock()
        self.service = ImproveUserMessageService(self.mock_client_class)
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Test Contact")
        self.user = User.objects.create_user(
            email="agent@test.com", password="testpass123"
        )
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )

    def _create_message(self, text="Hello"):
        return Message.objects.create(
            room=self.room,
            user=self.user,
            text=text,
        )

    def test_register_message_improvement_creates_status(self):
        message = self._create_message()

        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )

        self.assertTrue(
            MessageImprovementStatus.objects.filter(message=message).exists()
        )
        improvement = MessageImprovementStatus.objects.get(message=message)
        self.assertEqual(
            improvement.type, ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING
        )
        self.assertEqual(improvement.status, ImprovedUserMessageStatusChoices.USED)

    def test_register_message_improvement_with_discarded_status(self):
        message = self._create_message()

        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
            status=ImprovedUserMessageStatusChoices.DISCARDED,
        )

        improvement = MessageImprovementStatus.objects.get(message=message)
        self.assertEqual(improvement.type, ImprovedUserMessageTypeChoices.MORE_EMPATHY)
        self.assertEqual(improvement.status, ImprovedUserMessageStatusChoices.DISCARDED)

    def test_register_message_improvement_with_edited_status(self):
        message = self._create_message()

        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.CLARITY,
            status=ImprovedUserMessageStatusChoices.EDITED,
        )

        improvement = MessageImprovementStatus.objects.get(message=message)
        self.assertEqual(improvement.type, ImprovedUserMessageTypeChoices.CLARITY)
        self.assertEqual(improvement.status, ImprovedUserMessageStatusChoices.EDITED)

    def test_register_message_improvement_skips_duplicate(self):
        message = self._create_message()

        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )
        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
            status=ImprovedUserMessageStatusChoices.DISCARDED,
        )

        self.assertEqual(
            MessageImprovementStatus.objects.filter(message=message).count(), 1
        )
        improvement = MessageImprovementStatus.objects.get(message=message)
        self.assertEqual(
            improvement.type, ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING
        )
        self.assertEqual(improvement.status, ImprovedUserMessageStatusChoices.USED)

    def test_register_message_improvement_different_messages(self):
        message_1 = self._create_message(text="First message")
        message_2 = self._create_message(text="Second message")

        self.service.register_message_improvement(
            message=message_1,
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )
        self.service.register_message_improvement(
            message=message_2,
            improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
            status=ImprovedUserMessageStatusChoices.EDITED,
        )

        self.assertEqual(MessageImprovementStatus.objects.count(), 2)
        self.assertEqual(
            MessageImprovementStatus.objects.get(message=message_1).type,
            ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
        )
        self.assertEqual(
            MessageImprovementStatus.objects.get(message=message_2).type,
            ImprovedUserMessageTypeChoices.MORE_EMPATHY,
        )

    def test_register_message_improvement_duplicate_logs_warning(self):
        message = self._create_message()

        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )

        with self.assertLogs(
            "chats.apps.ai_features.improve_user_message.services",
            level="WARNING",
        ) as log:
            self.service.register_message_improvement(
                message=message,
                improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
                status=ImprovedUserMessageStatusChoices.DISCARDED,
            )

        self.assertTrue(any("already registered" in entry for entry in log.output))

    def test_register_message_improvement_returns_none_on_duplicate(self):
        message = self._create_message()

        self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )

        result = self.service.register_message_improvement(
            message=message,
            improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
            status=ImprovedUserMessageStatusChoices.DISCARDED,
        )

        self.assertIsNone(result)


class GetImprovementFeaturePromptConfigTests(TestCase):
    def setUp(self):
        cache.clear()
        self.service = ImproveUserMessageService(MagicMock())

    def test_returns_feature_prompt_for_valid_type(self):
        feature_prompt = FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix grammar: {message}",
            version=1,
        )

        result = self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING
        )

        self.assertEqual(result, feature_prompt)

    def test_returns_latest_version(self):
        FeaturePrompt.objects.create(
            feature="more_empathy",
            model="old-model",
            prompt="Old prompt: {message}",
            version=1,
        )
        latest = FeaturePrompt.objects.create(
            feature="more_empathy",
            model="new-model",
            prompt="New prompt: {message}",
            version=2,
        )

        result = self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.MORE_EMPATHY
        )

        self.assertEqual(result, latest)
        self.assertEqual(result.model, "new-model")

    def test_raises_for_invalid_improvement_type(self):
        with self.assertRaises(ValueError) as ctx:
            self.service._get_improvement_feature_prompt_config("INVALID_TYPE")

        self.assertIn("Invalid improvement type", str(ctx.exception))

    def test_raises_when_no_feature_prompt_exists(self):
        with self.assertRaises(ValueError) as ctx:
            self.service._get_improvement_feature_prompt_config(
                ImprovedUserMessageTypeChoices.CLARITY
            )

        self.assertIn("No feature prompt found", str(ctx.exception))

    def test_works_for_all_valid_improvement_types(self):
        for choice in ImprovedUserMessageTypeChoices:
            feature_name = {
                ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING: "grammar_and_spelling",
                ImprovedUserMessageTypeChoices.MORE_EMPATHY: "more_empathy",
                ImprovedUserMessageTypeChoices.CLARITY: "clarity",
            }[choice]

            FeaturePrompt.objects.create(
                feature=feature_name,
                model="test-model",
                prompt=f"Prompt for {feature_name}: {{message}}",
                version=1,
            )

            result = self.service._get_improvement_feature_prompt_config(choice)
            self.assertEqual(result.feature, feature_name)

    def test_caches_feature_prompt(self):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix grammar: {message}",
            version=1,
        )

        self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING
        )

        cached = cache.get("ai_features:improve_user_message:grammar_and_spelling")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.feature, "grammar_and_spelling")

    def test_returns_cached_prompt_without_hitting_db(self):
        feature_prompt = FeaturePrompt.objects.create(
            feature="clarity",
            model="test-model",
            prompt="Improve clarity: {message}",
            version=1,
        )

        self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.CLARITY
        )

        FeaturePrompt.objects.all().delete()

        result = self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.CLARITY
        )
        self.assertEqual(result.pk, feature_prompt.pk)

    def test_does_not_cache_when_no_prompt_exists(self):
        with self.assertRaises(ValueError):
            self.service._get_improvement_feature_prompt_config(
                ImprovedUserMessageTypeChoices.CLARITY
            )

        cached = cache.get("ai_features:improve_user_message:clarity")
        self.assertIsNone(cached)

    @override_settings(IMPROVE_USER_MESSAGE_FEATURE_PROMPT_CACHE_TTL=1)
    def test_cache_uses_configured_ttl(self):
        FeaturePrompt.objects.create(
            feature="more_empathy",
            model="test-model",
            prompt="Add empathy: {message}",
            version=1,
        )

        self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.MORE_EMPATHY
        )

        cached = cache.get("ai_features:improve_user_message:more_empathy")
        self.assertIsNotNone(cached)

    def test_cache_key_is_per_feature_name(self):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="model-a",
            prompt="Fix: {message}",
            version=1,
        )
        FeaturePrompt.objects.create(
            feature="clarity",
            model="model-b",
            prompt="Clarify: {message}",
            version=1,
        )

        self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING
        )
        self.service._get_improvement_feature_prompt_config(
            ImprovedUserMessageTypeChoices.CLARITY
        )

        cached_grammar = cache.get(
            "ai_features:improve_user_message:grammar_and_spelling"
        )
        cached_clarity = cache.get("ai_features:improve_user_message:clarity")

        self.assertEqual(cached_grammar.model, "model-a")
        self.assertEqual(cached_clarity.model, "model-b")


@patch(
    "chats.apps.ai_features.improve_user_message.services.is_feature_active_for_attributes",
    return_value=True,
)
class GenerateImprovedMessageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.mock_client_class = MagicMock()
        self.mock_client_instance = MagicMock()
        self.mock_client_class.return_value = self.mock_client_instance
        self.service = ImproveUserMessageService(self.mock_client_class)
        self.project = Project.objects.create(name="Test Project")

    def test_generates_improved_message(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix the grammar of this text: {message}",
            settings={"temperature": 0.5},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "Improved text"

        result = self.service.generate_improved_message(
            user_message_text="hello wrold",
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            project=self.project,
        )

        self.assertEqual(result, "Improved text")
        self.mock_client_class.assert_called_once_with("test-model")
        self.mock_client_instance.generate_text.assert_called_once()

    def test_passes_correct_prompt_messages(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="clarity",
            model="test-model",
            prompt="Improve clarity: {message}",
            settings={"temperature": 0.3},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "Clear text"

        self.service.generate_improved_message(
            user_message_text="unclear text",
            improvement_type=ImprovedUserMessageTypeChoices.CLARITY,
            project=self.project,
        )

        call_args = self.mock_client_instance.generate_text.call_args
        settings_arg = call_args[0][0]
        prompt_msgs_arg = call_args[0][1]

        self.assertEqual(settings_arg, {"temperature": 0.3})
        self.assertEqual(len(prompt_msgs_arg), 2)
        self.assertEqual(
            prompt_msgs_arg[0],
            PromptMessage(text="Improve clarity: ", should_cache=True),
        )
        self.assertEqual(
            prompt_msgs_arg[1], PromptMessage(text="unclear text", should_cache=False)
        )

    def test_includes_suffix_after_message_placeholder(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="clarity",
            model="test-model",
            prompt="Improve this: {message}. Be concise and formal.",
            settings={"temperature": 0.3},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "Improved text"

        self.service.generate_improved_message(
            user_message_text="some text",
            improvement_type=ImprovedUserMessageTypeChoices.CLARITY,
            project=self.project,
        )

        call_args = self.mock_client_instance.generate_text.call_args
        prompt_msgs_arg = call_args[0][1]

        self.assertEqual(len(prompt_msgs_arg), 3)
        self.assertEqual(
            prompt_msgs_arg[0],
            PromptMessage(text="Improve this: ", should_cache=True),
        )
        self.assertEqual(
            prompt_msgs_arg[1],
            PromptMessage(text="some text", should_cache=False),
        )
        self.assertEqual(
            prompt_msgs_arg[2],
            PromptMessage(text=". Be concise and formal.", should_cache=True),
        )

    def test_no_suffix_when_placeholder_is_at_end(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="clarity",
            model="test-model",
            prompt="Improve this: {message}",
            settings={"temperature": 0.3},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "Improved text"

        self.service.generate_improved_message(
            user_message_text="some text",
            improvement_type=ImprovedUserMessageTypeChoices.CLARITY,
            project=self.project,
        )

        call_args = self.mock_client_instance.generate_text.call_args
        prompt_msgs_arg = call_args[0][1]

        self.assertEqual(len(prompt_msgs_arg), 2)

    def test_raises_when_prompt_missing_message_placeholder(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix the grammar of this text",
            version=1,
        )

        with self.assertRaises(ValueError) as ctx:
            self.service.generate_improved_message(
                user_message_text="hello",
                improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
                project=self.project,
            )

        self.assertIn("{message}", str(ctx.exception))

    def test_raises_when_prompt_has_multiple_message_placeholders(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix: {message} and also {message}",
            version=1,
        )

        with self.assertRaises(ValueError) as ctx:
            self.service.generate_improved_message(
                user_message_text="hello",
                improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
                project=self.project,
            )

        self.assertIn("exactly one", str(ctx.exception))

    def test_uses_latest_feature_prompt_version(self, _mock_ff):
        FeaturePrompt.objects.create(
            feature="more_empathy",
            model="old-model",
            prompt="Old: {message}",
            settings={"temperature": 0.9},
            version=1,
        )
        FeaturePrompt.objects.create(
            feature="more_empathy",
            model="new-model",
            prompt="New: {message}",
            settings={"temperature": 0.7},
            version=2,
        )
        self.mock_client_instance.generate_text.return_value = "Empathetic text"

        self.service.generate_improved_message(
            user_message_text="cold text",
            improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
            project=self.project,
        )

        self.mock_client_class.assert_called_once_with("new-model")

    def test_raises_when_feature_flag_is_inactive(self, mock_ff):
        mock_ff.return_value = False

        with self.assertRaises(FeatureFlagInactiveError) as ctx:
            self.service.generate_improved_message(
                user_message_text="hello",
                improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
                project=self.project,
            )

        self.assertIn("Feature flag is not active for this project", str(ctx.exception))

    def test_feature_flag_called_with_project_uuid(self, mock_ff):
        FeaturePrompt.objects.create(
            feature="grammar_and_spelling",
            model="test-model",
            prompt="Fix: {message}",
            settings={"temperature": 0.5},
            version=1,
        )
        self.mock_client_instance.generate_text.return_value = "Improved text"

        self.service.generate_improved_message(
            user_message_text="hello",
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            project=self.project,
        )

        mock_ff.assert_called_once_with(
            "weniChatsAITextImprovement",
            {"projectUUID": str(self.project.uuid)},
        )
