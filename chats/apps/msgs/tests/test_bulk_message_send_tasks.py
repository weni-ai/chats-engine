from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.msgs.tasks import process_bulk_message_send, send_bulk_message_to_room
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class ProcessBulkMessageSendTaskTests(TestCase):
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
        self.room_one = Room.objects.create(
            contact=Contact.objects.create(name="Contact 1"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        self.room_two = Room.objects.create(
            contact=Contact.objects.create(name="Contact 2"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        self.bulk_send = BulkMessageSend.objects.create(
            user=self.requester,
            project=self.project,
            text="Bulk hello",
            filter_snapshot={"queues": [], "agents": []},
            status=BulkMessageSendStatus.PENDING,
        )

    @patch("chats.apps.msgs.tasks.send_bulk_message_to_room.delay")
    @patch("chats.apps.msgs.tasks.get_bulk_send_rooms_usecase")
    def test_sets_status_to_processing_and_dispatches_per_room(
        self, mock_usecase, mock_delay
    ):
        mock_queryset = MagicMock()
        mock_queryset.values_list.return_value = [
            self.room_one.uuid,
            self.room_two.uuid,
        ]
        mock_usecase.execute.return_value = mock_queryset

        process_bulk_message_send.run(self.bulk_send.uuid)

        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.PROCESSING)
        mock_usecase.execute.assert_called_once()
        called_bulk_send = mock_usecase.execute.call_args[0][0]
        self.assertEqual(called_bulk_send.uuid, self.bulk_send.uuid)
        mock_queryset.values_list.assert_called_once_with("uuid", flat=True)
        self.assertEqual(mock_delay.call_count, 2)
        mock_delay.assert_any_call(self.bulk_send.uuid, self.room_one.uuid)
        mock_delay.assert_any_call(self.bulk_send.uuid, self.room_two.uuid)

    @patch("chats.apps.msgs.tasks.send_bulk_message_to_room.delay")
    @patch("chats.apps.msgs.tasks.get_bulk_send_rooms_usecase")
    def test_does_not_dispatch_when_no_rooms(self, mock_usecase, mock_delay):
        mock_queryset = MagicMock()
        mock_queryset.values_list.return_value = []
        mock_usecase.execute.return_value = mock_queryset

        process_bulk_message_send.run(self.bulk_send.uuid)

        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.PROCESSING)
        mock_delay.assert_not_called()


class SendBulkMessageToRoomTaskTests(TestCase):
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
        self.room = Room.objects.create(
            contact=Contact.objects.create(name="Contact"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        self.bulk_send = BulkMessageSend.objects.create(
            user=self.requester,
            project=self.project,
            text="Bulk hello",
            filter_snapshot={"queues": [], "agents": []},
            status=BulkMessageSendStatus.PROCESSING,
        )

    def test_loads_bulk_send_and_room_without_error(self):
        result = send_bulk_message_to_room.run(self.bulk_send.uuid, self.room.uuid)

        self.assertIsNone(result)
        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.PROCESSING)

    def test_raises_when_bulk_send_does_not_exist(self):
        missing_uuid = "00000000-0000-0000-0000-000000000001"
        with self.assertRaises(BulkMessageSend.DoesNotExist):
            send_bulk_message_to_room.run(missing_uuid, self.room.uuid)

    def test_raises_when_room_does_not_exist(self):
        missing_uuid = "00000000-0000-0000-0000-000000000002"
        with self.assertRaises(Room.DoesNotExist):
            send_bulk_message_to_room.run(self.bulk_send.uuid, missing_uuid)
