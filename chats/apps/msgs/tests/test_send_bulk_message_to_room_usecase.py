from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendStatus,
    Message,
)
from chats.apps.msgs.usecases.send_bulk_message_to_room import (
    SendBulkMessageToRoomUseCase,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class SendBulkMessageToRoomUseCaseTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            email="requester@test.com",
            password="testpass123",
            first_name="Requester",
            last_name="User",
        )
        self.agent = User.objects.create_user(
            email="agent@test.com",
            password="testpass123",
            first_name="Agent",
            last_name="User",
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
        self.text = "Bulk hello"
        self.bulk_send = BulkMessageSend.objects.create(
            user=self.requester,
            project=self.project,
            text=self.text,
            filter_snapshot={"queues": [], "agents": []},
            status=BulkMessageSendStatus.PROCESSING,
        )
        self.usecase = SendBulkMessageToRoomUseCase()

    def _create_room(self, user=None):
        return Room.objects.create(
            contact=Contact.objects.create(name="Contact"),
            queue=self.queue,
            user=user,
            is_active=True,
        )

    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_sends_message_as_room_user_when_assigned(self, mock_notify_room):
        room = self._create_room(user=self.agent)

        with self.captureOnCommitCallbacks(execute=True):
            message = self.usecase.execute(self.bulk_send, room)

        self.assertEqual(message.user, self.agent)
        self.assertIsNone(message.contact)
        self.assertEqual(message.text, self.text)
        self.assertEqual(message.room, room)

        link = BulkMessageSendMessage.objects.get(message=message)
        self.assertEqual(link.bulk_message_send, self.bulk_send)

        room.refresh_from_db()
        self.assertEqual(room.last_message, message)
        self.assertEqual(room.last_message_user, self.agent)

        mock_notify_room.assert_called_once_with("create", True)

    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_sends_message_with_empty_user_when_unassigned(self, mock_notify_room):
        room = self._create_room(user=None)

        with self.captureOnCommitCallbacks(execute=True):
            message = self.usecase.execute(self.bulk_send, room)

        self.assertIsNone(message.user)
        self.assertIsNone(message.contact)
        self.assertEqual(message.text, self.text)

        self.assertTrue(
            BulkMessageSendMessage.objects.filter(
                bulk_message_send=self.bulk_send,
                message=message,
            ).exists()
        )

        room.refresh_from_db()
        self.assertEqual(room.last_message, message)
        self.assertIsNone(room.last_message_user)

        mock_notify_room.assert_called_once_with("create", True)

    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_does_not_notify_before_commit(self, mock_notify_room):
        room = self._create_room(user=self.agent)

        with self.captureOnCommitCallbacks(execute=False):
            self.usecase.execute(self.bulk_send, room)

        mock_notify_room.assert_not_called()
        self.assertEqual(Message.objects.count(), 1)
