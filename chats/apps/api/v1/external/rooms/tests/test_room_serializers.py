from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.external.rooms.serializers import (
    RoomFlowSerializer,
    get_room_user,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class GetRoomUserTests(TestCase):
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
            name="Test Contact",
            email="contact@test.com",
            external_id="ext-contact-123",
        )
        self.permission = ProjectPermission.objects.create(
            user=self.user, project=self.project, role=1, status="ONLINE"
        )

    def test_get_room_user_no_flowstart_no_linked_user(self):
        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        self.assertIsNone(result)

    def test_get_room_user_with_user_online(self):
        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=self.user,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        self.assertEqual(result, self.user)

    def test_get_room_user_with_user_offline(self):
        self.permission.status = "OFFLINE"
        self.permission.save()

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=self.user,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        self.assertIsNone(result)

    def test_get_room_user_with_rooms_waiting_in_queue(self):
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=None, is_active=True
        )

        result = get_room_user(
            contact=Contact.objects.create(
                name="Contact 2", email="contact2@test.com", external_id="ext-2"
            ),
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        self.assertIsNone(result)

    def test_get_room_user_falls_back_to_available_agent(self):
        with patch.object(
            self.queue, "get_available_agent", return_value=self.user
        ) as mock_get_agent:
            get_room_user(
                contact=self.contact,
                queue=self.queue,
                user=None,
                groups=[],
                is_created=True,
                flow_uuid=None,
                project=self.project,
            )

            mock_get_agent.assert_called_once()


class ProcessMessageHistoryTests(TestCase):
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
        self.now = timezone.now()

    def test_process_message_history_creates_messages(self):
        serializer = RoomFlowSerializer()

        messages_data = [
            {"text": "Hello", "direction": "incoming", "created_on": self.now}
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "trigger_default_message"):
                with patch.object(self.room, "increment_unread_messages_count"):
                    serializer.process_message_history(self.room, messages_data)

        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)

    def test_process_message_history_with_attachments(self):
        from chats.apps.msgs.models import MessageMedia

        serializer = RoomFlowSerializer()

        messages_data = [
            {
                "text": "Image attached",
                "direction": "incoming",
                "created_on": self.now,
                "attachments": [
                    {"content_type": "image/png", "url": "http://example.com/image.png"}
                ],
            }
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "trigger_default_message"):
                with patch.object(self.room, "increment_unread_messages_count"):
                    serializer.process_message_history(self.room, messages_data)

        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)
        self.assertEqual(MessageMedia.objects.count(), 1)

    def test_process_message_history_without_text_and_media_raises_error(self):
        from rest_framework import serializers

        serializer_instance = RoomFlowSerializer()

        messages_data = [
            {"direction": "incoming", "text": None, "created_on": self.now}
        ]

        with self.assertRaises(serializers.ValidationError) as context:
            serializer_instance.process_message_history(self.room, messages_data)

        self.assertIn("text or media", str(context.exception).lower())

    def test_process_message_history_outgoing_does_not_set_contact(self):
        serializer = RoomFlowSerializer()

        messages_data = [
            {"text": "Agent reply", "direction": "outgoing", "created_on": self.now}
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "increment_unread_messages_count"):
                serializer.process_message_history(self.room, messages_data)

        message = Message.objects.get(room=self.room)
        self.assertIsNone(message.contact)

    def test_process_message_history_incoming_sets_contact(self):
        serializer = RoomFlowSerializer()

        messages_data = [
            {
                "text": "Customer message",
                "direction": "incoming",
                "created_on": self.now,
            }
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "trigger_default_message"):
                with patch.object(self.room, "increment_unread_messages_count"):
                    serializer.process_message_history(self.room, messages_data)

        message = Message.objects.get(room=self.room)
        self.assertEqual(message.contact, self.contact)

    def test_process_message_history_triggers_default_message_when_no_user(self):
        self.room.user = None
        self.room.save()

        serializer = RoomFlowSerializer()

        messages_data = [
            {"text": "Hello", "direction": "incoming", "created_on": self.now}
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "trigger_default_message") as mock_trigger:
                with patch.object(self.room, "increment_unread_messages_count"):
                    serializer.process_message_history(self.room, messages_data)

                mock_trigger.assert_called_once()

    def test_process_message_history_increments_unread_count(self):
        serializer = RoomFlowSerializer()

        messages_data = [
            {"text": "Message 1", "direction": "incoming", "created_on": self.now},
            {"text": "Message 2", "direction": "incoming", "created_on": self.now},
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "trigger_default_message"):
                with patch.object(
                    self.room, "increment_unread_messages_count"
                ) as mock_increment:
                    serializer.process_message_history(self.room, messages_data)

                    mock_increment.assert_called_once()
                    call_args = mock_increment.call_args
                    self.assertEqual(call_args[0][0], 2)

    def test_process_message_history_with_multiple_attachments(self):
        from chats.apps.msgs.models import MessageMedia

        serializer = RoomFlowSerializer()

        messages_data = [
            {
                "text": "Multiple files",
                "direction": "incoming",
                "created_on": self.now,
                "attachments": [
                    {"content_type": "image/png", "url": "http://example.com/1.png"},
                    {"content_type": "image/jpg", "url": "http://example.com/2.jpg"},
                ],
            }
        ]

        with patch.object(self.room, "notify_room"):
            with patch.object(self.room, "trigger_default_message"):
                with patch.object(self.room, "increment_unread_messages_count"):
                    serializer.process_message_history(self.room, messages_data)

        self.assertEqual(MessageMedia.objects.count(), 2)

    def test_process_message_history_empty_messages(self):
        serializer = RoomFlowSerializer()

        messages_data = []

        serializer.process_message_history(self.room, messages_data)

        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)
