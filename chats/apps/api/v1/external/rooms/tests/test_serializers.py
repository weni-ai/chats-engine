from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from chats.apps.accounts.models import User
from chats.apps.api.v1.external.rooms.serializers import RoomFlowSerializer, get_room_user
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestProcessMessageHistory(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="test-contact-123", name="Test Contact"
        )
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, urn="whatsapp:+5511999999999"
        )
        self.serializer = RoomFlowSerializer()
        self.now = timezone.now()

    @patch.object(Room, "notify_room")
    def test_creates_outgoing_message(self, mock_notify):
        messages_data = [
            {"direction": "outgoing", "text": "Hello", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)
        message = Message.objects.get(room=self.room)
        self.assertEqual(message.text, "Hello")
        self.assertIsNone(message.contact)
        mock_notify.assert_called_once_with("create")

    @patch.object(Room, "notify_room")
    def test_creates_incoming_message_with_contact(self, mock_notify):
        messages_data = [
            {"direction": "incoming", "text": "Hi there", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

        message = Message.objects.get(room=self.room)
        self.assertEqual(message.text, "Hi there")
        self.assertEqual(message.contact, self.contact)

    @patch.object(Room, "notify_room")
    def test_creates_multiple_messages(self, mock_notify):
        messages_data = [
            {"direction": "incoming", "text": "Hello", "attachments": [], "created_on": self.now},
            {"direction": "outgoing", "text": "Hi", "attachments": [], "created_on": self.now},
            {"direction": "incoming", "text": "How are you?", "attachments": [], "created_on": self.now},
        ]

        self.serializer.process_message_history(self.room, messages_data)

        self.assertEqual(Message.objects.filter(room=self.room).count(), 3)

    def test_raises_error_when_message_has_no_text_or_media(self):
        messages_data = [{"direction": "incoming", "text": None, "attachments": [], "created_on": self.now}]

        with self.assertRaises(ValidationError) as context:
            self.serializer.process_message_history(self.room, messages_data)

        self.assertIn("Cannot create message without text or media", str(context.exception))

    @patch.object(Room, "notify_room")
    def test_creates_message_with_media(self, mock_notify):
        messages_data = [
            {
                "direction": "incoming",
                "text": "Check this image",
                "attachments": [
                    {"content_type": "image/png", "url": "https://example.com/image.png"}
                ],
                "created_on": self.now,
            }
        ]

        self.serializer.process_message_history(self.room, messages_data)

        message = Message.objects.get(room=self.room)
        media = MessageMedia.objects.get(message=message)
        self.assertEqual(media.content_type, "image/png")
        self.assertEqual(media.media_url, "https://example.com/image.png")

    @patch.object(Room, "notify_room")
    def test_creates_message_without_text_but_with_media(self, mock_notify):
        messages_data = [
            {
                "direction": "incoming",
                "text": None,
                "attachments": [
                    {"content_type": "image/jpeg", "url": "https://example.com/photo.jpg"}
                ],
                "created_on": self.now,
            }
        ]

        self.serializer.process_message_history(self.room, messages_data)

        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)
        self.assertEqual(MessageMedia.objects.count(), 1)

    @patch.object(Room, "notify_room")
    def test_creates_multiple_media_for_single_message(self, mock_notify):
        messages_data = [
            {
                "direction": "incoming",
                "text": "Multiple files",
                "attachments": [
                    {"content_type": "image/png", "url": "https://example.com/1.png"},
                    {"content_type": "image/png", "url": "https://example.com/2.png"},
                    {"content_type": "application/pdf", "url": "https://example.com/doc.pdf"},
                ],
                "created_on": self.now,
            }
        ]

        self.serializer.process_message_history(self.room, messages_data)

        message = Message.objects.get(room=self.room)
        self.assertEqual(MessageMedia.objects.filter(message=message).count(), 3)

    @patch.object(Room, "notify_room")
    @patch.object(Room, "get_is_waiting", return_value=True)
    def test_updates_is_waiting_on_incoming_message(self, mock_is_waiting, mock_notify):
        self.room.is_waiting = True
        self.room.save()

        messages_data = [
            {"direction": "incoming", "text": "Hello", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

        self.room.refresh_from_db()
        self.assertFalse(self.room.is_waiting)

    @patch.object(Room, "notify_room")
    @patch.object(Room, "get_is_waiting", return_value=False)
    def test_does_not_update_room_when_not_waiting(self, mock_is_waiting, mock_notify):
        self.room.is_waiting = False
        self.room.save()

        messages_data = [
            {"direction": "outgoing", "text": "Hello", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

    @patch.object(Room, "notify_room")
    @patch.object(Room, "trigger_default_message")
    def test_triggers_default_message_for_incoming_without_user(
        self, mock_trigger, mock_notify
    ):
        self.room.user = None
        self.room.save()

        messages_data = [
            {"direction": "incoming", "text": "Hello", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

        mock_trigger.assert_called_once()

    @patch.object(Room, "notify_room")
    @patch.object(Room, "trigger_default_message")
    def test_does_not_trigger_default_message_when_room_has_user(
        self, mock_trigger, mock_notify
    ):
        user = User.objects.create(email="agent@test.com")
        self.room.user = user
        self.room.save()

        messages_data = [
            {"direction": "incoming", "text": "Hello", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

        mock_trigger.assert_not_called()

    @patch.object(Room, "notify_room")
    @patch.object(Room, "trigger_default_message")
    def test_does_not_trigger_default_message_for_outgoing_only(
        self, mock_trigger, mock_notify
    ):
        messages_data = [
            {"direction": "outgoing", "text": "Hello", "attachments": [], "created_on": self.now}
        ]

        self.serializer.process_message_history(self.room, messages_data)

        mock_trigger.assert_not_called()

    @patch.object(Room, "notify_room")
    def test_does_not_notify_when_no_messages(self, mock_notify):
        messages_data = []

        self.serializer.process_message_history(self.room, messages_data)

        mock_notify.assert_not_called()


class TestGetRoomUser(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="test-contact-123", name="Test Contact"
        )
        self.user = User.objects.create(email="agent@test.com")
        self.permission = ProjectPermission.objects.create(
            project=self.project, user=self.user, role=1, status="ONLINE"
        )

    def test_returns_none_when_no_flowstart_and_no_user(self):
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

    def test_returns_user_when_passed_and_online(self):
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

    def test_returns_none_when_user_is_offline(self):
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

    @patch("chats.apps.api.v1.external.rooms.serializers.start_queue_priority_routing")
    def test_returns_none_when_queue_not_empty_with_priority_routing(
        self, mock_start_routing
    ):
        from chats.apps.projects.models.models import RoomRoutingType
        self.project.room_routing_type = RoomRoutingType.QUEUE_PRIORITY
        self.project.save()

        Room.objects.create(queue=self.queue, is_active=True, user=None)

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
        mock_start_routing.assert_called_once_with(self.queue)

    @patch.object(Queue, "get_available_agent")
    def test_returns_available_agent_when_queue_empty_with_priority_routing(
        self, mock_get_agent
    ):
        from chats.apps.projects.models.models import RoomRoutingType
        self.project.room_routing_type = RoomRoutingType.QUEUE_PRIORITY
        self.project.save()

        mock_get_agent.return_value = self.user

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        self.assertEqual(result, self.user)
        mock_get_agent.assert_called_once()

    def test_returns_none_when_rooms_waiting_in_queue(self):
        Room.objects.create(queue=self.queue, is_active=True, user=None)

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

    @patch.object(Queue, "get_available_agent")
    def test_returns_available_agent_when_no_rooms_waiting(self, mock_get_agent):
        mock_get_agent.return_value = self.user

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        self.assertEqual(result, self.user)

    def test_returns_flowstart_user_when_online(self):
        from chats.apps.projects.models import FlowStart, ContactGroupFlowReference

        flow_start = FlowStart.objects.create(
            project=self.project, flow="test-flow-uuid", permission=self.permission
        )
        ContactGroupFlowReference.objects.create(
            flow_start=flow_start, external_id=self.contact.external_id, receiver_type="contact"
        )

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid="test-flow-uuid",
            project=self.project,
        )

        self.assertEqual(result, self.user)

    def test_returns_none_when_flowstart_user_is_offline(self):
        from chats.apps.projects.models import FlowStart, ContactGroupFlowReference

        self.permission.status = "OFFLINE"
        self.permission.save()

        flow_start = FlowStart.objects.create(
            project=self.project, flow="test-flow-uuid", permission=self.permission
        )
        ContactGroupFlowReference.objects.create(
            flow_start=flow_start, external_id=self.contact.external_id, receiver_type="contact"
        )

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid="test-flow-uuid",
            project=self.project,
        )

        self.assertIsNone(result)

    @patch.object(Contact, "get_linked_user")
    def test_returns_linked_user_when_online_and_not_created(self, mock_linked_user):
        mock_linked_permission = MagicMock()
        mock_linked_permission.is_online = True
        mock_linked_permission.user = self.user
        mock_linked_user.return_value = mock_linked_permission

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=False,
            flow_uuid=None,
            project=self.project,
        )

        self.assertEqual(result, self.user)

    @patch.object(Contact, "get_linked_user")
    def test_ignores_linked_user_when_is_created(self, mock_linked_user):
        mock_linked_permission = MagicMock()
        mock_linked_permission.is_online = True
        mock_linked_permission.user = self.user
        mock_linked_user.return_value = mock_linked_permission

        Room.objects.create(queue=self.queue, is_active=True, user=None)

        result = get_room_user(
            contact=self.contact,
            queue=self.queue,
            user=None,
            groups=[],
            is_created=True,
            flow_uuid=None,
            project=self.project,
        )

        mock_linked_user.assert_not_called()
