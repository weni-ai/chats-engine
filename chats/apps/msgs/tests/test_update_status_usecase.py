from unittest.mock import MagicMock, patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    MessageStatusNotifier,
    UpdateStatusMessageUseCase,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class MessageStatusNotifierTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector", project=self.project, rooms_limit=10
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create_user(
            email="agent@test.com", first_name="Agent", last_name="Test"
        )
        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )

    @patch("chats.apps.msgs.usecases.UpdateStatusMessageUseCase.send_channels_group")
    def test_notify_status_update(self, mock_send):
        MessageStatusNotifier.notify_status_update(
            message_uuid="test-uuid", message_status="read", permission_pk=1
        )
        mock_send.assert_called_once()

    @patch("chats.apps.msgs.usecases.UpdateStatusMessageUseCase.send_channels_group")
    def test_notify_for_message_without_room(self, mock_send):
        message = MagicMock()
        message.room = None
        result = MessageStatusNotifier.notify_for_message(message, "read")
        self.assertFalse(result)
        mock_send.assert_not_called()

    @patch("chats.apps.msgs.usecases.UpdateStatusMessageUseCase.send_channels_group")
    def test_notify_for_message_without_user(self, mock_send):
        message = MagicMock()
        message.room = MagicMock()
        message.room.user = None
        result = MessageStatusNotifier.notify_for_message(message, "read")
        self.assertFalse(result)
        mock_send.assert_not_called()


class UpdateStatusMessageUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector", project=self.project, rooms_limit=10
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create_user(
            email="agent@test.com", first_name="Agent", last_name="Test"
        )
        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        self.usecase = UpdateStatusMessageUseCase()

    def test_update_status_message_adds_to_queue(self):
        self.usecase.update_status_message("msg-123", "read")
        self.assertEqual(len(self.usecase._msgs), 1)
        self.assertEqual(self.usecase._msgs[0]["message_id"], "msg-123")
        self.assertEqual(self.usecase._msgs[0]["message_status"], "read")

    def test_bulk_create_with_empty_queue(self):
        self.usecase._bulk_create()

    def test_bulk_create_with_invalid_message_data(self):
        self.usecase._msgs.append(None)
        self.usecase._msgs.append({})
        self.usecase._msgs.append({"message_id": None})
        self.usecase._bulk_create()

    @patch(
        "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.MessageStatusNotifier.notify_for_message"
    )
    def test_bulk_create_with_valid_message_read_status(self, mock_notify):
        message = Message.objects.create(
            room=self.room, text="Test message", user=self.user
        )
        ChatMessageReplyIndex.objects.create(external_id="ext-123", message=message)

        self.usecase._msgs.append({"message_id": "ext-123", "message_status": "READ"})
        self.usecase._bulk_create()

        message.refresh_from_db()
        self.assertEqual(message.is_read, "read")

    @patch(
        "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.MessageStatusNotifier.notify_for_message"
    )
    def test_bulk_create_with_valid_message_delivered_status(self, mock_notify):
        message = Message.objects.create(
            room=self.room, text="Test message", user=self.user
        )
        ChatMessageReplyIndex.objects.create(external_id="ext-456", message=message)

        self.usecase._msgs.append(
            {"message_id": "ext-456", "message_status": "DELIVERED"}
        )
        self.usecase._bulk_create()

        message.refresh_from_db()
        self.assertEqual(message.is_delivered, "delivered")

    @patch(
        "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.MessageStatusNotifier.notify_for_message"
    )
    def test_bulk_create_with_v_status(self, mock_notify):
        message = Message.objects.create(
            room=self.room, text="Test message", user=self.user
        )
        ChatMessageReplyIndex.objects.create(external_id="ext-789", message=message)

        self.usecase._msgs.append({"message_id": "ext-789", "message_status": "V"})
        self.usecase._bulk_create()

        message.refresh_from_db()
        self.assertEqual(message.is_read, "read")

    @patch(
        "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.MessageStatusNotifier.notify_for_message"
    )
    def test_bulk_create_with_d_status(self, mock_notify):
        message = Message.objects.create(
            room=self.room, text="Test message", user=self.user
        )
        ChatMessageReplyIndex.objects.create(external_id="ext-aaa", message=message)

        self.usecase._msgs.append({"message_id": "ext-aaa", "message_status": "D"})
        self.usecase._bulk_create()

        message.refresh_from_db()
        self.assertEqual(message.is_delivered, "delivered")

    def test_bulk_create_with_nonexistent_message(self):
        self.usecase._msgs.append(
            {"message_id": "nonexistent-123", "message_status": "READ"}
        )
        self.usecase._bulk_create()

    @patch(
        "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.MessageStatusNotifier.notify_for_message"
    )
    def test_bulk_create_groups_messages_by_update_fields(self, mock_notify):
        message1 = Message.objects.create(
            room=self.room, text="Test message 1", user=self.user
        )
        ChatMessageReplyIndex.objects.create(
            external_id="ext-group-1", message=message1
        )

        message2 = Message.objects.create(
            room=self.room, text="Test message 2", user=self.user
        )
        ChatMessageReplyIndex.objects.create(
            external_id="ext-group-2", message=message2
        )

        self.usecase._msgs.append(
            {"message_id": "ext-group-1", "message_status": "READ"}
        )
        self.usecase._msgs.append(
            {"message_id": "ext-group-2", "message_status": "READ"}
        )
        self.usecase._bulk_create()

        message1.refresh_from_db()
        message2.refresh_from_db()
        self.assertEqual(message1.is_read, "read")
        self.assertEqual(message2.is_read, "read")

    def test_bulk_create_skips_already_read_message(self):
        message = Message.objects.create(
            room=self.room, text="Test message", user=self.user, is_read="read"
        )
        ChatMessageReplyIndex.objects.create(
            external_id="ext-already-read", message=message
        )

        self.usecase._msgs.append(
            {"message_id": "ext-already-read", "message_status": "READ"}
        )
        self.usecase._bulk_create()

    def test_bulk_create_skips_already_delivered_message(self):
        message = Message.objects.create(
            room=self.room,
            text="Test message",
            user=self.user,
            is_delivered="delivered",
        )
        ChatMessageReplyIndex.objects.create(
            external_id="ext-already-delivered", message=message
        )

        self.usecase._msgs.append(
            {"message_id": "ext-already-delivered", "message_status": "DELIVERED"}
        )
        self.usecase._bulk_create()

    @patch("chats.apps.msgs.usecases.UpdateStatusMessageUseCase.settings")
    def test_update_status_triggers_bulk_at_threshold(self, mock_settings):
        mock_settings.MESSAGE_BULK_SIZE = 2

        usecase = UpdateStatusMessageUseCase()

        with patch.object(usecase, "_bulk_create") as mock_bulk:
            usecase._msgs.append({"message_id": "1", "message_status": "READ"})
            usecase.update_status_message("2", "READ")

            mock_bulk.assert_called_once()
