from django.test import TestCase

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
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class ImproveUserMessageServiceTests(TestCase):
    def setUp(self):
        self.service = ImproveUserMessageService()
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
            improvement_type=ImprovedUserMessageTypeChoices.MORE_CLARITY,
            status=ImprovedUserMessageStatusChoices.EDITED,
        )

        improvement = MessageImprovementStatus.objects.get(message=message)
        self.assertEqual(improvement.type, ImprovedUserMessageTypeChoices.MORE_CLARITY)
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
