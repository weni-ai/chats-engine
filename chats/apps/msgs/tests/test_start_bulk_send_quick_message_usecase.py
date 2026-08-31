import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.msgs.models import (
    BulkQuickMessageSend,
    BulkQuickMessageSendStatus,
    Message,
)
from chats.apps.msgs.usecases.start_bulk_send_quick_message import (
    StartBulkSendQuickMessageUseCase,
)
from chats.apps.projects.models import Project

User = get_user_model()


class StartBulkSendQuickMessageUseCaseTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            email="requester@test.com",
            password="testpass123",
            first_name="Requester",
            last_name="User",
        )
        self.project = Project.objects.create(name="Test Project")
        self.usecase = StartBulkSendQuickMessageUseCase()
        self.text = "Quick hello"
        self.contact_one = uuid.uuid4()
        self.contact_two = uuid.uuid4()

    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_creates_pending_bulk_quick_message_send_with_contacts(self, mock_delay):
        bulk_send = self.usecase.execute(
            user_email=self.requester.email,
            text=self.text,
            project_uuid=self.project.uuid,
            contacts=[self.contact_one, self.contact_two],
        )

        self.assertIsInstance(bulk_send, BulkQuickMessageSend)
        self.assertEqual(bulk_send.status, BulkQuickMessageSendStatus.PENDING)
        self.assertEqual(bulk_send.user, self.requester)
        self.assertEqual(bulk_send.project, self.project)
        self.assertEqual(bulk_send.text, self.text)
        self.assertEqual(
            bulk_send.contacts,
            [str(self.contact_one), str(self.contact_two)],
        )
        self.assertEqual(Message.objects.count(), 0)
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_null_contacts_are_stored_as_null(self, mock_delay):
        bulk_send = self.usecase.execute(
            user_email=self.requester.email,
            text=self.text,
            project_uuid=self.project.uuid,
            contacts=None,
        )

        self.assertIsNone(bulk_send.contacts)
        self.assertEqual(bulk_send.status, BulkQuickMessageSendStatus.PENDING)
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_empty_contacts_are_stored_as_empty_list(self, mock_delay):
        bulk_send = self.usecase.execute(
            user_email=self.requester.email,
            text=self.text,
            project_uuid=self.project.uuid,
            contacts=[],
        )

        self.assertEqual(bulk_send.contacts, [])
        self.assertEqual(bulk_send.status, BulkQuickMessageSendStatus.PENDING)
        mock_delay.assert_called_once_with(bulk_send.uuid)

    def test_raises_when_user_email_does_not_exist(self):
        with self.assertRaises(User.DoesNotExist):
            self.usecase.execute(
                user_email="missing@test.com",
                text=self.text,
                project_uuid=self.project.uuid,
                contacts=None,
            )

        self.assertEqual(BulkQuickMessageSend.objects.count(), 0)

    def test_raises_when_project_uuid_does_not_exist(self):
        with self.assertRaises(Project.DoesNotExist):
            self.usecase.execute(
                user_email=self.requester.email,
                text=self.text,
                project_uuid=uuid.uuid4(),
                contacts=None,
            )

        self.assertEqual(BulkQuickMessageSend.objects.count(), 0)
