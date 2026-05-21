import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import AutomaticMessage, Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.sectors.services import AutomaticMessagesService


class _BaseAutoMessageTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="AM Project")
        self.sector = Sector.objects.create(
            name="AM Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            is_automatic_message_active=True,
            automatic_message_text="Default text",
        )
        self.queue = Queue.objects.create(name="AM Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="AM Contact")
        self.user = User.objects.create(email="am-agent@test.com")
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )

    def _service(self):
        return AutomaticMessagesService()


class TestSendAutomaticMessageEarlyReturns(_BaseAutoMessageTestCase):
    def test_returns_false_when_automatic_disabled(self):
        self.sector.is_automatic_message_active = False
        self.sector.save()

        result = self._service().send_automatic_message(
            self.room, "hi", self.user
        )
        self.assertFalse(result)
        self.assertFalse(Message.objects.filter(room=self.room).exists())

    def test_returns_false_when_no_default_text(self):
        self.sector.automatic_message_text = ""
        self.sector.save()

        result = self._service().send_automatic_message(
            self.room, "hi", self.user
        )
        self.assertFalse(result)

    def test_returns_false_when_user_message_already_exists(self):
        Message.objects.create(room=self.room, user=self.user, text="manual")

        result = self._service().send_automatic_message(
            self.room, "hi", self.user
        )
        self.assertFalse(result)
        # Pre-existing message remains; no automatic message was created
        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)
        self.assertFalse(
            AutomaticMessage.objects.filter(room=self.room).exists()
        )

    def test_returns_false_when_automatic_message_already_exists(self):
        existing_msg = Message.objects.create(
            room=self.room, user=self.user, text="prior"
        )
        AutomaticMessage.objects.create(room=self.room, message=existing_msg)

        result = self._service().send_automatic_message(
            self.room, "hi", self.user
        )
        self.assertFalse(result)


class TestSendAutomaticMessageHappyPath(_BaseAutoMessageTestCase):
    def test_creates_message_and_returns_true(self):
        result = self._service().send_automatic_message(
            self.room, "Hello!", self.user
        )

        self.assertTrue(result)
        msg = Message.objects.get(room=self.room, user=self.user)
        self.assertEqual(msg.text, "Hello!")
        self.assertTrue(
            AutomaticMessage.objects.filter(room=self.room, message=msg).exists()
        )
        self.room.refresh_from_db()
        self.assertIsNotNone(self.room.automatic_message_sent_at)


class TestSendAutomaticMessageExceptionPath(_BaseAutoMessageTestCase):
    @patch("chats.apps.sectors.services.Message.objects.create")
    def test_returns_false_when_message_creation_raises(self, mock_create):
        mock_create.side_effect = RuntimeError("db down")

        result = self._service().send_automatic_message(
            self.room, "Hello", self.user
        )

        self.assertFalse(result)


class TestSendAutomaticMessageTicketCheck(_BaseAutoMessageTestCase):
    def setUp(self):
        super().setUp()
        self.room.ticket_uuid = uuid.uuid4()
        self.room.save()

    @patch("chats.apps.sectors.services.time.sleep", return_value=None)
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_proceeds_when_ticket_is_found(
        self, mock_flows_client_class, _mock_sleep
    ):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"results": [{"id": "ticket-1"}]}
        mock_flows_client_class.return_value.get_ticket.return_value = response

        result = self._service().send_automatic_message(
            self.room, "Hello", self.user, check_ticket=True
        )

        self.assertTrue(result)
        mock_flows_client_class.return_value.get_ticket.assert_called()

    @patch("chats.apps.sectors.services.FLOWS_GET_TICKET_RETRIES", 1)
    @patch("chats.apps.sectors.services.time.sleep", return_value=None)
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_raises_when_ticket_not_found_after_retries(
        self, mock_flows_client_class, _mock_sleep
    ):
        response = MagicMock()
        response.status_code = 404
        mock_flows_client_class.return_value.get_ticket.return_value = response

        with self.assertRaises(Exception):
            self._service().send_automatic_message(
                self.room, "Hello", self.user, check_ticket=True
            )

    @patch("chats.apps.sectors.services.FLOWS_GET_TICKET_RETRIES", 0)
    @patch("chats.apps.sectors.services.time.sleep", return_value=None)
    @patch("chats.apps.sectors.services.FlowRESTClient")
    def test_uses_secondary_project_when_configured(
        self, mock_flows_client_class, _mock_sleep
    ):
        secondary = Project.objects.create(
            name="AM Secondary",
        )
        self.sector.secondary_project = {"uuid": str(secondary.uuid)}
        self.sector.save()

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"results": [{"id": "ticket-1"}]}
        mock_flows_client_class.return_value.get_ticket.return_value = response

        result = self._service().send_automatic_message(
            self.room, "Hello", self.user, check_ticket=True
        )
        self.assertTrue(result)

        called_project = mock_flows_client_class.return_value.get_ticket.call_args[
            0
        ][0]
        self.assertEqual(str(called_project.uuid), str(secondary.uuid))
