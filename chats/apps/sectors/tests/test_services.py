import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase

from chats.apps.sectors.services import AutomaticMessagesService
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.msgs.models import Message, AutomaticMessage


class TestAutomaticMessagesService(TestCase):
    def setUp(self):
        self.service = AutomaticMessagesService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.user = User.objects.create(email="test@test.com")

    def test_send_automatic_message_when_sector_automatic_message_is_not_active(self):
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_sector_automatic_message_text_is_not_set(self):
        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = ""
        self.sector.save()
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_room_already_has_automatic_message(self):
        AutomaticMessage.objects.create(
            room=self.room,
            message=Message.objects.create(
                room=self.room,
                text=self.sector.automatic_message_text,
                user=self.user,
                contact=None,
            ),
        )
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_room_already_has_messages(self):
        Message.objects.create(
            room=self.room,
            text=self.sector.automatic_message_text,
            user=self.user,
            contact=None,
        )
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_all_conditions_are_met(self):
        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = "Test Message"
        self.sector.save()
        self.assertTrue(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )


@patch("chats.apps.sectors.services.FLOWS_GET_TICKET_RETRIES", 2)
class TestAutomaticMessagesServiceCheckTicket(TestCase):
    def setUp(self):
        self.service = AutomaticMessagesService()
        self.project = Project.objects.create(name="Test Project")
        self.secondary_project = Project.objects.create(name="Secondary Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            is_automatic_message_active=True,
            automatic_message_text="Welcome!",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.ticket_uuid = uuid.uuid4()
        self.room = Room.objects.create(queue=self.queue, ticket_uuid=self.ticket_uuid)
        self.user = User.objects.create(email="agent@test.com")

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_success_on_first_attempt(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"uuid": "ticket-123"}]}
        mock_client_class.return_value.get_ticket.return_value = mock_response

        result = self.service.send_automatic_message(
            self.room, "Test Message", self.user, check_ticket=True
        )

        self.assertTrue(result)
        mock_client_class.return_value.get_ticket.assert_called_once_with(
            self.project, self.ticket_uuid
        )

    @patch("chats.apps.sectors.services.time.sleep")
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_success_after_retry(self, mock_client_class, mock_sleep):
        mock_not_found = MagicMock()
        mock_not_found.status_code = 200
        mock_not_found.json.return_value = {"results": []}

        mock_found = MagicMock()
        mock_found.status_code = 200
        mock_found.json.return_value = {"results": [{"uuid": "ticket-123"}]}

        mock_client_class.return_value.get_ticket.side_effect = [
            mock_not_found,
            mock_found,
        ]

        result = self.service.send_automatic_message(
            self.room, "Test Message", self.user, check_ticket=True
        )

        self.assertTrue(result)
        self.assertEqual(mock_client_class.return_value.get_ticket.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("chats.apps.sectors.services.time.sleep")
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_raises_exception_after_max_retries(
        self, mock_client_class, mock_sleep
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client_class.return_value.get_ticket.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.service.send_automatic_message(
                self.room, "Test Message", self.user, check_ticket=True
            )

        self.assertIn("ticket", str(context.exception).lower())
        self.assertIn("not found", str(context.exception).lower())
        self.assertEqual(mock_client_class.return_value.get_ticket.call_count, 3)

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_uses_secondary_project_when_configured(
        self, mock_client_class
    ):
        self.sector.secondary_project = {"uuid": str(self.secondary_project.uuid)}
        self.sector.save()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"uuid": "ticket-123"}]}
        mock_client_class.return_value.get_ticket.return_value = mock_response

        result = self.service.send_automatic_message(
            self.room, "Test Message", self.user, check_ticket=True
        )

        self.assertTrue(result)
        mock_client_class.return_value.get_ticket.assert_called_once_with(
            self.secondary_project, self.ticket_uuid
        )

    @patch("chats.apps.sectors.services.time.sleep")
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_exponential_backoff(self, mock_client_class, mock_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client_class.return_value.get_ticket.return_value = mock_response

        with self.assertRaises(Exception):
            self.service.send_automatic_message(
                self.room, "Test Message", self.user, check_ticket=True
            )

        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_skipped_when_no_ticket_uuid(self, mock_client_class):
        self.room.ticket_uuid = None
        self.room.save()

        result = self.service.send_automatic_message(
            self.room, "Test Message", self.user, check_ticket=True
        )

        self.assertTrue(result)
        mock_client_class.return_value.get_ticket.assert_not_called()

    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_skipped_when_check_ticket_false(self, mock_client_class):
        result = self.service.send_automatic_message(
            self.room, "Test Message", self.user, check_ticket=False
        )

        self.assertTrue(result)
        mock_client_class.return_value.get_ticket.assert_not_called()

    @patch("chats.apps.sectors.services.time.sleep")
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_check_ticket_handles_non_200_response(self, mock_client_class, mock_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client_class.return_value.get_ticket.return_value = mock_response

        with self.assertRaises(Exception):
            self.service.send_automatic_message(
                self.room, "Test Message", self.user, check_ticket=True
            )

    @patch("chats.apps.sectors.services.time.sleep")
    @patch("chats.apps.sectors.services.FlowRESTClient")
    @patch("chats.apps.sectors.services.capture_exception")
    def test_check_ticket_captures_json_parse_exception(
        self, mock_capture, mock_client_class, mock_sleep
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client_class.return_value.get_ticket.return_value = mock_response

        with self.assertRaises(Exception):
            self.service.send_automatic_message(
                self.room, "Test Message", self.user, check_ticket=True
            )

        self.assertTrue(mock_capture.called)
