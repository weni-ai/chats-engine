from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.rooms.services.bulk_transfer_service import (
    BulkTransferResult,
    BulkTransferService,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class BulkTransferResultTestCase(TestCase):
    def test_initial_state_is_zero(self):
        result = BulkTransferResult()
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failed_rooms, [])

    def test_add_success_increments_counter(self):
        result = BulkTransferResult()
        result.add_success()
        result.add_success()
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)

    def test_add_failure_increments_counter_and_stores_data(self):
        result = BulkTransferResult()
        result.add_failure("uuid-abc", "permission denied")
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.success_count, 0)
        self.assertIn("permission denied", result.errors)
        self.assertIn("uuid-abc", result.failed_rooms)

    def test_to_dict_with_empty_result(self):
        result = BulkTransferResult()
        data = result.to_dict()
        self.assertEqual(data["success_count"], 0)
        self.assertEqual(data["failed_count"], 0)
        self.assertEqual(data["total_processed"], 0)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["failed_rooms"], [])
        self.assertFalse(data["has_more_errors"])

    def test_to_dict_total_processed_is_sum(self):
        result = BulkTransferResult()
        result.add_success()
        result.add_failure("x", "err")
        data = result.to_dict()
        self.assertEqual(data["total_processed"], 2)

    def test_to_dict_errors_truncated_at_10(self):
        result = BulkTransferResult()
        for i in range(15):
            result.add_failure(f"room-{i}", f"error {i}")
        data = result.to_dict()
        self.assertEqual(len(data["errors"]), 10)
        self.assertEqual(len(data["failed_rooms"]), 10)
        self.assertTrue(data["has_more_errors"])


class BulkTransferServiceTransferHistoryTestCase(TestCase):
    """
    Tests that ensure every transfer path in BulkTransferService persists
    the transfer into both `full_transfer_history` and legacy
    `transfer_history`, matching the single-room transfer behavior.
    """

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.queue2 = Queue.objects.create(name="Queue 2", sector=self.sector)

        self.user_request = User.objects.create_user(
            email="requester@test.com", password="pw"
        )
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")
        self.other_agent = User.objects.create_user(
            email="other@test.com", password="pw"
        )

        ProjectPermission.objects.create(
            user=self.agent, project=self.project, role=2
        )
        ProjectPermission.objects.create(
            user=self.other_agent, project=self.project, role=2
        )
        ProjectPermission.objects.create(
            user=self.user_request, project=self.project, role=2
        )

        self.contact1 = Contact.objects.create(name="Contact 1")
        self.contact2 = Contact.objects.create(name="Contact 2")
        self.contact3 = Contact.objects.create(name="Contact 3")

        self.service = BulkTransferService()

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_transfer_user_only_appends_to_full_transfer_history(
        self, mock_ws, mock_feedback, mock_waiting, mock_routing
    ):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        self.assertEqual(room.full_transfer_history, [])
        self.assertIsNone(room.transfer_history)

        result = self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            user=self.agent,
        )

        self.assertEqual(result.success_count, 1)
        room.refresh_from_db()
        self.assertEqual(len(room.full_transfer_history), 1)
        self.assertEqual(room.full_transfer_history[0]["action"], "transfer")
        self.assertIsNotNone(room.transfer_history)
        self.assertEqual(room.transfer_history["action"], "transfer")

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_transfer_queue_only_appends_to_full_transfer_history(
        self, mock_ws, mock_feedback, mock_waiting, mock_routing
    ):
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact1,
            is_active=True,
            user=self.other_agent,
        )

        result = self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            queue=self.queue2,
        )

        self.assertEqual(result.success_count, 1)
        room.refresh_from_db()
        self.assertEqual(len(room.full_transfer_history), 1)
        self.assertEqual(room.full_transfer_history[0]["action"], "transfer")
        self.assertIsNotNone(room.transfer_history)

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_transfer_user_and_queue_appends_two_entries_to_history(
        self, mock_ws, mock_feedback, mock_waiting, mock_routing
    ):
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact1,
            is_active=True,
            user=self.other_agent,
        )

        result = self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            user=self.agent,
            queue=self.queue2,
        )

        self.assertEqual(result.success_count, 1)
        room.refresh_from_db()
        # Two entries: one for queue change, one for user change
        self.assertEqual(len(room.full_transfer_history), 2)
        self.assertEqual(room.full_transfer_history[0]["action"], "transfer")
        self.assertEqual(room.full_transfer_history[1]["action"], "transfer")

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_history_appended_per_room_across_batch(
        self, mock_ws, mock_feedback, mock_waiting, mock_routing
    ):
        room1 = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        room2 = Room.objects.create(
            queue=self.queue, contact=self.contact2, is_active=True
        )

        result = self.service.transfer(
            Room.objects.filter(is_active=True),
            user_request=self.user_request,
            user=self.agent,
        )

        self.assertEqual(result.success_count, 2)

        for room in [room1, room2]:
            room.refresh_from_db()
            self.assertEqual(len(room.full_transfer_history), 1)
            self.assertIsNotNone(room.transfer_history)

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_history_grows_on_successive_transfers(
        self, mock_ws, mock_feedback, mock_waiting, mock_routing
    ):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )

        self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            user=self.agent,
        )
        self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            queue=self.queue2,
        )

        room.refresh_from_db()
        # 1 from user-only transfer + 1 from queue-only transfer
        self.assertEqual(len(room.full_transfer_history), 2)

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_legacy_full_transfer_history_none_is_handled(
        self, mock_ws, mock_feedback, mock_waiting, mock_routing
    ):
        """
        Rooms created before the `default=list` migration may have
        `full_transfer_history = None`. The service must not crash.
        """
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        # Simulate a legacy row without an initial list
        Room.objects.filter(pk=room.pk).update(full_transfer_history=None)

        result = self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            user=self.agent,
        )

        self.assertEqual(result.success_count, 1)
        room.refresh_from_db()
        self.assertEqual(len(room.full_transfer_history), 1)


class BulkTransferServiceValidationTestCase(TestCase):
    """
    Tests that ensure validation short-circuits bulk transfer without
    mutating the transfer history.
    """

    def setUp(self):
        self.project = Project.objects.create(name="Project A")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)

        self.other_project = Project.objects.create(name="Project B")
        self.other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.other_queue = Queue.objects.create(
            name="Other Queue", sector=self.other_sector
        )

        self.user_request = User.objects.create_user(
            email="req@test.com", password="pw"
        )
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")

        ProjectPermission.objects.create(
            user=self.user_request, project=self.project, role=2
        )

        self.contact = Contact.objects.create(name="C1")
        self.service = BulkTransferService()

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.utils.websockets.send_channels_group")
    def test_queue_from_different_project_is_rejected(self, mock_ws, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, is_active=True
        )

        result = self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            queue=self.other_queue,
        )

        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 1)
        room.refresh_from_db()
        self.assertEqual(room.full_transfer_history, [])
        self.assertIsNone(room.transfer_history)

    @patch("chats.apps.api.v1.rooms.services.bulk_transfer_service.start_queue_priority_routing")
    @patch("chats.utils.websockets.send_channels_group")
    def test_user_without_permission_is_rejected(self, mock_ws, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, is_active=True
        )

        result = self.service.transfer(
            Room.objects.filter(pk=room.pk),
            user_request=self.user_request,
            user=self.agent,
        )

        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 1)
        room.refresh_from_db()
        self.assertEqual(room.full_transfer_history, [])
