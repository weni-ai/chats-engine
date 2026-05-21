import uuid
from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageStatusChoices,
    ImprovedUserMessageTypeChoices,
)
from chats.apps.ai_features.improve_user_message.tasks import (
    register_message_improvement_task,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestRegisterMessageImprovementTask(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="IMP Test Project")
        self.sector = Sector.objects.create(
            name="IMP Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="IMP Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="IMP Contact")
        self.user = User.objects.create_user(
            email="imp-agent@test.com", password="x"
        )
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user, is_active=True
        )
        self.message = Message.objects.create(
            room=self.room, user=self.user, text="hi"
        )

    @patch(
        "chats.apps.ai_features.improve_user_message.tasks.ImproveUserMessageService"
    )
    def test_calls_service_register_method(self, mock_service_class):
        register_message_improvement_task(
            message_uuid=str(self.message.uuid),
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )

        mock_service_class.assert_called_once_with(integration_client_class=None)
        mock_service_class.return_value.register_message_improvement.assert_called_once_with(
            message=self.message,
            improvement_type=ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
            status=ImprovedUserMessageStatusChoices.USED,
        )

    @patch(
        "chats.apps.ai_features.improve_user_message.tasks.ImproveUserMessageService"
    )
    def test_returns_silently_when_message_does_not_exist(self, mock_service_class):
        result = register_message_improvement_task(
            message_uuid=str(uuid.uuid4()),
            improvement_type=ImprovedUserMessageTypeChoices.MORE_EMPATHY,
            status=ImprovedUserMessageStatusChoices.DISCARDED,
        )

        self.assertIsNone(result)
        mock_service_class.assert_not_called()
