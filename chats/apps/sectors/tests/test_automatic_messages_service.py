import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import AutomaticMessage, Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.sectors.services import AutomaticMessagesService


@override_settings(AUTOMATIC_MESSAGE_FLOWS_GET_TICKET_RETRIES=1)
class AutomaticMessagesServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            is_automatic_message_active=True,
            automatic_message_text="Hello, welcome!",
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
        self.service = AutomaticMessagesService()

    def test_send_automatic_message_when_feature_disabled(self):
        self.sector.is_automatic_message_active = False
        self.sector.save()

        result = self.service.send_automatic_message(
            room=self.room, message="Test message", user=self.user
        )

        self.assertFalse(result)

    def test_send_automatic_message_when_no_message_text(self):
        self.sector.automatic_message_text = None
        self.sector.save()

        result = self.service.send_automatic_message(
            room=self.room, message="Test message", user=self.user
        )

        self.assertFalse(result)

    def test_send_automatic_message_when_already_has_automatic_message(self):
        message = Message.objects.create(
            room=self.room, text="First message", user=self.user
        )
        AutomaticMessage.objects.create(room=self.room, message=message)

        result = self.service.send_automatic_message(
            room=self.room, message="Test message", user=self.user
        )

        self.assertFalse(result)

    def test_send_automatic_message_when_room_has_user_messages(self):
        Message.objects.create(room=self.room, text="User message", user=self.user)

        result = self.service.send_automatic_message(
            room=self.room, message="Test message", user=self.user
        )

        self.assertFalse(result)

    @patch("chats.apps.sectors.services.Message.notify_room")
    def test_send_automatic_message_success(self, mock_notify):
        result = self.service.send_automatic_message(
            room=self.room, message="Test message", user=self.user
        )

        self.assertTrue(result)
        self.assertTrue(Message.objects.filter(room=self.room).exists())
        self.assertTrue(AutomaticMessage.objects.filter(room=self.room).exists())

    @patch("chats.apps.sectors.services.Message.notify_room")
    def test_send_automatic_message_creates_message_with_correct_data(
        self, mock_notify
    ):
        test_message = "Welcome to our support!"
        self.service.send_automatic_message(
            room=self.room, message=test_message, user=self.user
        )

        message = Message.objects.get(room=self.room)
        self.assertEqual(message.text, test_message)
        self.assertEqual(message.user, self.user)
        self.assertIsNone(message.contact)

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_send_automatic_message_with_check_ticket_finds_ticket(self, mock_client):
        ticket_uuid = uuid.uuid4()
        Room.objects.filter(uuid=self.room.uuid).update(ticket_uuid=ticket_uuid)
        self.room.refresh_from_db()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"uuid": str(ticket_uuid)}]}
        mock_client.return_value.get_ticket.return_value = mock_response

        with patch("chats.apps.sectors.services.Message.notify_room"):
            result = self.service.send_automatic_message(
                room=self.room,
                message="Test message",
                user=self.user,
                check_ticket=True,
            )

        self.assertTrue(result)

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_send_automatic_message_with_check_ticket_not_found_raises_exception(
        self, mock_client
    ):
        ticket_uuid = uuid.uuid4()
        Room.objects.filter(uuid=self.room.uuid).update(ticket_uuid=ticket_uuid)
        self.room.refresh_from_db()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.return_value.get_ticket.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.service.send_automatic_message(
                room=self.room,
                message="Test message",
                user=self.user,
                check_ticket=True,
            )

        self.assertIn("ticket", str(context.exception).lower())

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_send_automatic_message_with_check_ticket_retries(self, mock_client):
        ticket_uuid = uuid.uuid4()
        Room.objects.filter(uuid=self.room.uuid).update(ticket_uuid=ticket_uuid)
        self.room.refresh_from_db()

        mock_response_not_found = MagicMock()
        mock_response_not_found.status_code = 200
        mock_response_not_found.json.return_value = {"results": []}

        mock_response_found = MagicMock()
        mock_response_found.status_code = 200
        mock_response_found.json.return_value = {
            "results": [{"uuid": str(ticket_uuid)}]
        }

        mock_client.return_value.get_ticket.side_effect = [
            mock_response_not_found,
            mock_response_found,
        ]

        with patch("chats.apps.sectors.services.Message.notify_room"):
            with patch("chats.apps.sectors.services.time.sleep"):
                result = self.service.send_automatic_message(
                    room=self.room,
                    message="Test message",
                    user=self.user,
                    check_ticket=True,
                )

        self.assertTrue(result)

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_send_automatic_message_with_secondary_project(self, mock_client):
        secondary_project = Project.objects.create(
            name="Secondary Project", timezone="UTC"
        )
        self.sector.secondary_project = {"uuid": str(secondary_project.uuid)}
        self.sector.save()

        ticket_uuid = uuid.uuid4()
        Room.objects.filter(uuid=self.room.uuid).update(ticket_uuid=ticket_uuid)
        self.room.refresh_from_db()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"uuid": str(ticket_uuid)}]}
        mock_client.return_value.get_ticket.return_value = mock_response

        with patch("chats.apps.sectors.services.Message.notify_room"):
            result = self.service.send_automatic_message(
                room=self.room,
                message="Test message",
                user=self.user,
                check_ticket=True,
            )

        self.assertTrue(result)
        mock_client.return_value.get_ticket.assert_called_once_with(
            secondary_project, ticket_uuid
        )

    def test_send_automatic_message_without_ticket_check_skips_ticket_validation(self):
        Room.objects.filter(uuid=self.room.uuid).update(ticket_uuid=None)
        self.room.refresh_from_db()

        with patch("chats.apps.sectors.services.Message.notify_room"):
            result = self.service.send_automatic_message(
                room=self.room,
                message="Test message",
                user=self.user,
                check_ticket=False,
            )

        self.assertTrue(result)
