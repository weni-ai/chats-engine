from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.rooms.services.bulk_take_service import (
    BulkTakeResult,
    BulkTakeService,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class BulkTakeResultTestCase(TestCase):
    def test_initial_state_is_zero(self):
        result = BulkTakeResult()
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failed_rooms, [])

    def test_add_success_increments_counter(self):
        result = BulkTakeResult()
        result.add_success()
        result.add_success()
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)

    def test_add_failure_increments_counter_and_stores_data(self):
        result = BulkTakeResult()
        result.add_failure("uuid-123", "already assigned")
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.success_count, 0)
        self.assertIn("already assigned", result.errors)
        self.assertIn("uuid-123", result.failed_rooms)

    def test_to_dict_with_empty_result(self):
        result = BulkTakeResult()
        data = result.to_dict()
        self.assertEqual(data["success_count"], 0)
        self.assertEqual(data["failed_count"], 0)
        self.assertEqual(data["total_processed"], 0)
        self.assertFalse(data["has_more_errors"])

    def test_to_dict_total_processed_is_sum(self):
        result = BulkTakeResult()
        result.add_success()
        result.add_failure("x", "err")
        data = result.to_dict()
        self.assertEqual(data["total_processed"], 2)

    def test_to_dict_errors_truncated_at_10(self):
        result = BulkTakeResult()
        for i in range(15):
            result.add_failure(f"room-{i}", f"error {i}")
        data = result.to_dict()
        self.assertEqual(len(data["errors"]), 10)
        self.assertTrue(data["has_more_errors"])


class BulkTakeServiceTestCase(TestCase):
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
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")

        # Contacts — unique per room (unique constraint: contact+queue+is_active)
        self.contact1 = Contact.objects.create(name="Contact 1")
        self.contact2 = Contact.objects.create(name="Contact 2")
        self.contact3 = Contact.objects.create(name="Contact 3")

        self.service = BulkTakeService()

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_empty_queryset_returns_zero_counts(self, mock_ws, mock_feedback, mock_routing):
        result = self.service.take(Room.objects.none(), self.agent)
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 0)
        mock_routing.assert_not_called()

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_unassigned_room_taken_successfully(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        result = self.service.take(Room.objects.filter(pk=room.pk), self.agent)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_room_user_is_set_to_provided_agent(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        self.service.take(Room.objects.filter(pk=room.pk), self.agent)

        room.refresh_from_db()
        self.assertEqual(room.user, self.agent)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_already_assigned_room_counted_as_failure(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        other_agent = User.objects.create_user(email="other@test.com", password="pw")
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True, user=other_agent
        )
        result = self.service.take(Room.objects.filter(pk=room.pk), self.agent)

        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.success_count, 0)
        self.assertTrue(any("already assigned" in e for e in result.errors))

        # User should remain unchanged
        room.refresh_from_db()
        self.assertEqual(room.user, other_agent)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_transfer_history_updated_after_take(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        self.service.take(Room.objects.filter(pk=room.pk), self.agent)

        room.refresh_from_db()
        self.assertIsNotNone(room.transfer_history)
        self.assertEqual(room.transfer_history.get("action"), "pick")
        self.assertIsNotNone(room.full_transfer_history)
        self.assertEqual(len(room.full_transfer_history), 1)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_feedback_message_created_for_each_room(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        room1 = Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        room2 = Room.objects.create(queue=self.queue, contact=self.contact2, is_active=True)

        self.service.take(Room.objects.filter(is_active=True), self.agent)

        self.assertEqual(mock_feedback.call_count, 2)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_queue_routing_triggered_once_per_queue(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        Room.objects.create(queue=self.queue, contact=self.contact2, is_active=True)

        self.service.take(Room.objects.filter(queue=self.queue, is_active=True), self.agent)

        mock_routing.assert_called_once_with(self.queue)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_queue_routing_triggered_per_distinct_queue(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        queue2 = Queue.objects.create(name="Queue 2", sector=self.sector)
        Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        Room.objects.create(queue=queue2, contact=self.contact2, is_active=True)

        self.service.take(Room.objects.filter(is_active=True), self.agent)

        self.assertEqual(mock_routing.call_count, 2)
        called_queues = {call.args[0] for call in mock_routing.call_args_list}
        self.assertEqual(called_queues, {self.queue, queue2})

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_mixed_assigned_and_unassigned_rooms(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        other_agent = User.objects.create_user(email="other@test.com", password="pw")
        free_room = Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        taken_room = Room.objects.create(
            queue=self.queue, contact=self.contact2, is_active=True, user=other_agent
        )

        result = self.service.take(Room.objects.filter(is_active=True), self.agent)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 1)

        free_room.refresh_from_db()
        self.assertEqual(free_room.user, self.agent)

        taken_room.refresh_from_db()
        self.assertEqual(taken_room.user, other_agent)

    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.calculate_last_queue_waiting_time", return_value=0)
    @patch("chats.apps.api.v1.rooms.services.bulk_take_service.create_room_feedback_message")
    @patch("chats.utils.websockets.send_channels_group")
    def test_post_take_ws_failure_does_not_count_as_take_failure(self, mock_ws, mock_feedback, mock_waiting, mock_routing):
        mock_ws.side_effect = Exception("WS down")
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        result = self.service.take(Room.objects.filter(pk=room.pk), self.agent)

        # Assignment succeeded, post-take WS failure is logged but not counted
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)
        room.refresh_from_db()
        self.assertEqual(room.user, self.agent)
