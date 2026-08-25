from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    BulkQuickMessageSend,
    BulkQuickMessageSendMessage,
    BulkQuickMessageSendMessageStatus,
    BulkQuickMessageSendStatus,
    Message,
)
from chats.apps.msgs.usecases.send_bulk_quick_message_to_room import (
    SendBulkQuickMessageToRoomUseCase,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class SendBulkQuickMessageToRoomUseCaseTests(TestCase):
    def setUp(self):
        self.attendant = User.objects.create_user(
            email="attendant@test.com",
            password="testpass123",
            first_name="Attendant",
            last_name="User",
        )
        self.other_agent = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            first_name="Other",
            last_name="Agent",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.text = "Quick hello"
        self.bulk_send = BulkQuickMessageSend.objects.create(
            user=self.attendant,
            project=self.project,
            text=self.text,
            contacts=None,
            status=BulkQuickMessageSendStatus.PROCESSING,
        )
        self.usecase = SendBulkQuickMessageToRoomUseCase()

    def _create_room(self, user=None, is_active=True):
        return Room.objects.create(
            contact=Contact.objects.create(name="Contact"),
            queue=self.queue,
            user=user,
            is_active=is_active,
        )

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.delay")
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_sends_message_as_requesting_attendant(
        self, mock_notify_room, mock_progress_delay
    ):
        room = self._create_room(user=self.attendant)

        with self.captureOnCommitCallbacks(execute=True):
            bulk_message = self.usecase.execute(self.bulk_send, room)

        message = bulk_message.message
        self.assertEqual(bulk_message.status, BulkQuickMessageSendMessageStatus.SUCCESS)
        self.assertEqual(bulk_message.room, room)
        self.assertIsNone(bulk_message.errors)
        self.assertEqual(message.user, self.attendant)
        self.assertIsNone(message.contact)
        self.assertEqual(message.text, self.text)
        self.assertEqual(message.room, room)

        link = BulkQuickMessageSendMessage.objects.get(message=message)
        self.assertEqual(link.bulk_quick_message_send, self.bulk_send)
        self.assertEqual(link.room, room)
        self.assertEqual(link.status, BulkQuickMessageSendMessageStatus.SUCCESS)

        room.refresh_from_db()
        self.assertEqual(room.last_message, message)
        self.assertEqual(room.last_message_user, self.attendant)

        mock_notify_room.assert_called_once_with("create", True)
        mock_progress_delay.assert_called_once_with(self.bulk_send.uuid)

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.delay")
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_does_not_notify_before_commit(
        self, mock_notify_room, mock_progress_delay
    ):
        room = self._create_room(user=self.attendant)

        with self.captureOnCommitCallbacks(execute=False):
            self.usecase.execute(self.bulk_send, room)

        mock_notify_room.assert_not_called()
        mock_progress_delay.assert_not_called()
        self.assertEqual(Message.objects.count(), 1)

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.delay")
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_fails_when_room_is_inactive(self, mock_notify_room, mock_progress_delay):
        room = self._create_room(user=self.attendant, is_active=False)

        with self.captureOnCommitCallbacks(execute=True):
            bulk_message = self.usecase.execute(self.bulk_send, room)

        self.assertEqual(bulk_message.status, BulkQuickMessageSendMessageStatus.FAILED)
        self.assertIsNone(bulk_message.message)
        self.assertEqual(bulk_message.room, room)
        self.assertEqual(bulk_message.bulk_quick_message_send, self.bulk_send)
        self.assertEqual(
            bulk_message.errors["error"], "Closed rooms can't receive messages"
        )
        self.assertEqual(bulk_message.errors["traceback"], "")
        self.assertEqual(Message.objects.count(), 0)
        mock_notify_room.assert_not_called()
        mock_progress_delay.assert_called_once_with(self.bulk_send.uuid)

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.delay")
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_fails_when_room_is_not_assigned_to_attendant(
        self, mock_notify_room, mock_progress_delay
    ):
        room = self._create_room(user=self.other_agent)

        with self.captureOnCommitCallbacks(execute=True):
            bulk_message = self.usecase.execute(self.bulk_send, room)

        self.assertEqual(bulk_message.status, BulkQuickMessageSendMessageStatus.FAILED)
        self.assertIsNone(bulk_message.message)
        self.assertEqual(
            bulk_message.errors["error"],
            "Room is not assigned to the requesting attendant",
        )
        self.assertEqual(Message.objects.count(), 0)
        mock_notify_room.assert_not_called()
        mock_progress_delay.assert_called_once_with(self.bulk_send.uuid)

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.delay")
    @patch("chats.apps.msgs.models.Message.notify_room")
    @patch(
        "chats.apps.msgs.usecases.send_bulk_quick_message_to_room.Message.objects.create"
    )
    def test_fails_when_message_create_raises(
        self, mock_create_message, mock_notify_room, mock_progress_delay
    ):
        room = self._create_room(user=self.attendant)
        mock_create_message.side_effect = RuntimeError("boom")

        with self.assertLogs(
            "chats.apps.msgs.usecases.send_bulk_quick_message_to_room",
            level="INFO",
        ) as logs:
            with self.captureOnCommitCallbacks(execute=True):
                bulk_message = self.usecase.execute(self.bulk_send, room)

        self.assertEqual(bulk_message.status, BulkQuickMessageSendMessageStatus.FAILED)
        self.assertIsNone(bulk_message.message)
        self.assertEqual(bulk_message.room, room)
        self.assertEqual(bulk_message.bulk_quick_message_send, self.bulk_send)
        self.assertEqual(bulk_message.errors["error"], "boom")
        self.assertIn("RuntimeError: boom", bulk_message.errors["traceback"])
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(BulkQuickMessageSendMessage.objects.count(), 1)
        self.assertTrue(
            any("Failed to send bulk quick" in message for message in logs.output)
        )
        mock_notify_room.assert_not_called()
        mock_progress_delay.assert_called_once_with(self.bulk_send.uuid)
