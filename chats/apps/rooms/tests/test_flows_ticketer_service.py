import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.exceptions import (
    FlowsChangeTicketerError,
    FlowsTicketerNotFoundError,
)
from chats.apps.rooms.flows_ticketer_service import change_ticketer_for_room
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


User = get_user_model()


HELPER_PATH = "chats.apps.rooms.flows_ticketer_service"


class ChangeTicketerForRoomTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Project")
        self.sector_a = Sector.objects.create(
            name="Sector A",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.sector_b = Sector.objects.create(
            name="Sector B",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue_a = Queue.objects.create(name="Q-A", sector=self.sector_a)
        self.queue_b = Queue.objects.create(name="Q-B", sector=self.sector_b)
        self.contact = Contact.objects.create(name="Contact")
        self.room = Room.objects.create(
            queue=self.queue_a,
            contact=self.contact,
            ticket_uuid=uuid.uuid4(),
            is_active=True,
        )

    @override_settings(USE_WENI_FLOWS=False)
    @patch(f"{HELPER_PATH}.FlowRESTClient")
    def test_noop_when_use_weni_flows_disabled(self, mock_client_cls):
        change_ticketer_for_room(self.room, str(self.sector_b.uuid))

        mock_client_cls.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch(f"{HELPER_PATH}.FlowRESTClient")
    def test_noop_when_room_has_no_ticket_uuid(self, mock_client_cls):
        self.room.ticket_uuid = None
        self.room.save()

        change_ticketer_for_room(self.room, str(self.sector_b.uuid))

        mock_client_cls.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch(f"{HELPER_PATH}.FlowRESTClient")
    def test_noop_when_destination_sector_is_the_same(self, mock_client_cls):
        change_ticketer_for_room(self.room, str(self.sector_a.uuid))

        mock_client_cls.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch(f"{HELPER_PATH}.FlowRESTClient")
    def test_calls_get_ticketer_then_change_ticketer(self, mock_client_cls):
        client = MagicMock()
        client.get_ticketer_by_sector.return_value = "ticketer-uuid"
        mock_client_cls.return_value = client

        change_ticketer_for_room(self.room, str(self.sector_b.uuid))

        client.get_ticketer_by_sector.assert_called_once_with(
            self.project, str(self.sector_b.uuid)
        )
        client.change_ticketer.assert_called_once_with(
            project=self.project,
            ticket_uuids=[str(self.room.ticket_uuid)],
            ticketer_uuid="ticketer-uuid",
        )

    @override_settings(USE_WENI_FLOWS=True)
    @patch(f"{HELPER_PATH}.capture_exception")
    @patch(f"{HELPER_PATH}.FlowRESTClient")
    def test_get_ticketer_failure_is_captured_and_reraised(
        self, mock_client_cls, mock_capture
    ):
        client = MagicMock()
        client.get_ticketer_by_sector.side_effect = (
            FlowsTicketerNotFoundError(sector_uuid=str(self.sector_b.uuid))
        )
        mock_client_cls.return_value = client

        with self.assertRaises(FlowsTicketerNotFoundError) as ctx:
            change_ticketer_for_room(self.room, str(self.sector_b.uuid))

        mock_capture.assert_called_once_with(ctx.exception)
        client.change_ticketer.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch(f"{HELPER_PATH}.capture_exception")
    @patch(f"{HELPER_PATH}.FlowRESTClient")
    def test_change_ticketer_failure_is_captured_and_reraised(
        self, mock_client_cls, mock_capture
    ):
        client = MagicMock()
        client.get_ticketer_by_sector.return_value = "ticketer-uuid"
        client.change_ticketer.side_effect = FlowsChangeTicketerError(
            ticket_uuids=[str(self.room.ticket_uuid)],
            ticketer_uuid="ticketer-uuid",
            status_code=500,
        )
        mock_client_cls.return_value = client

        with self.assertRaises(FlowsChangeTicketerError) as ctx:
            change_ticketer_for_room(self.room, str(self.sector_b.uuid))

        mock_capture.assert_called_once_with(ctx.exception)
