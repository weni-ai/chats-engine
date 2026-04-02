from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.rooms.services.bulk_close_service import (
    BulkCloseResult,
    BulkCloseService,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class BulkCloseResultTestCase(TestCase):
    def test_initial_state_is_zero(self):
        result = BulkCloseResult()
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failed_rooms, [])

    def test_add_success_increments_counter(self):
        result = BulkCloseResult()
        result.add_success()
        result.add_success()
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)

    def test_add_failure_increments_counter_and_stores_data(self):
        result = BulkCloseResult()
        result.add_failure("abc-123", "some error")
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.success_count, 0)
        self.assertIn("some error", result.errors)
        self.assertIn("abc-123", result.failed_rooms)

    def test_to_dict_with_empty_result(self):
        result = BulkCloseResult()
        data = result.to_dict()
        self.assertEqual(data["success_count"], 0)
        self.assertEqual(data["failed_count"], 0)
        self.assertEqual(data["total_processed"], 0)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["failed_rooms"], [])
        self.assertFalse(data["has_more_errors"])

    def test_to_dict_total_processed_is_sum(self):
        result = BulkCloseResult()
        result.add_success()
        result.add_success()
        result.add_failure("x", "err")
        data = result.to_dict()
        self.assertEqual(data["total_processed"], 3)
        self.assertEqual(data["success_count"], 2)
        self.assertEqual(data["failed_count"], 1)

    def test_to_dict_errors_truncated_at_10(self):
        result = BulkCloseResult()
        for i in range(15):
            result.add_failure(f"room-{i}", f"error {i}")
        data = result.to_dict()
        self.assertEqual(len(data["errors"]), 10)
        self.assertEqual(len(data["failed_rooms"]), 10)
        self.assertTrue(data["has_more_errors"])


class BulkCloseServiceTestCase(TestCase):
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
        self.contact1 = Contact.objects.create(name="Contact 1")
        self.contact2 = Contact.objects.create(name="Contact 2")
        self.contact3 = Contact.objects.create(name="Contact 3")
        self.service = BulkCloseService()

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_empty_queryset_returns_zero_counts(self, mock_ws, mock_close_room, mock_routing):
        result = self.service.close(Room.objects.none())
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 0)
        mock_routing.assert_not_called()
        mock_close_room.assert_not_called()

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_single_room_closed_successfully(self, mock_ws, mock_close_room, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        result = self.service.close(Room.objects.filter(pk=room.pk))

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)
        room.refresh_from_db()
        self.assertFalse(room.is_active)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_end_by_and_closed_by_passed_to_room_close(self, mock_ws, mock_close_room, mock_routing):
        agent = User.objects.create_user(email="agent@test.com", password="pw")
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        self.service.close(
            Room.objects.filter(pk=room.pk),
            end_by="agent",
            closed_by=agent,
        )
        room.refresh_from_db()
        self.assertEqual(room.ended_by, "agent")
        self.assertEqual(room.closed_by, agent)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_failed_room_counted_in_failed_count(self, mock_ws, mock_close_room, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        with patch.object(Room, "close", side_effect=Exception("close failed")):
            result = self.service.close(Room.objects.filter(pk=room.pk))

        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.success_count, 0)
        self.assertTrue(any("close failed" in e for e in result.errors))

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_queue_routing_triggered_once_per_queue(self, mock_ws, mock_close_room, mock_routing):
        Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        Room.objects.create(queue=self.queue, contact=self.contact2, is_active=True)

        self.service.close(Room.objects.filter(queue=self.queue, is_active=True))

        mock_routing.assert_called_once_with(self.queue)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_queue_routing_triggered_per_distinct_queue(self, mock_ws, mock_close_room, mock_routing):
        queue2 = Queue.objects.create(name="Queue 2", sector=self.sector)
        Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        Room.objects.create(queue=queue2, contact=self.contact2, is_active=True)

        self.service.close(Room.objects.filter(is_active=True))

        self.assertEqual(mock_routing.call_count, 2)
        called_queues = {call.args[0] for call in mock_routing.call_args_list}
        self.assertEqual(called_queues, {self.queue, queue2})

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_multiple_rooms_all_closed(self, mock_ws, mock_close_room, mock_routing):
        room1 = Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        room2 = Room.objects.create(queue=self.queue, contact=self.contact2, is_active=True)
        room3 = Room.objects.create(queue=self.queue, contact=self.contact3, is_active=True)

        result = self.service.close(Room.objects.filter(is_active=True))

        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.failed_count, 0)

        for room in [room1, room2, room3]:
            room.refresh_from_db()
            self.assertFalse(room.is_active)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_post_close_ws_failure_does_not_count_as_close_failure(self, mock_ws, mock_close_room, mock_routing):
        mock_ws.side_effect = Exception("WS down")
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        result = self.service.close(Room.objects.filter(pk=room.pk))

        # room.close() ran correctly, so it is counted as a success
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)
        room.refresh_from_db()
        self.assertFalse(room.is_active)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_close_room_metrics_called_for_each_successful_close(self, mock_ws, mock_close_room, mock_routing):
        room1 = Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)
        room2 = Room.objects.create(queue=self.queue, contact=self.contact2, is_active=True)

        self.service.close(Room.objects.filter(is_active=True))

        self.assertEqual(mock_close_room.call_count, 2)
        called_uuids = {call.args[0] for call in mock_close_room.call_args_list}
        self.assertIn(str(room1.uuid), called_uuids)
        self.assertIn(str(room2.uuid), called_uuids)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_tags_map_applied_to_room_on_close(self, mock_ws, mock_close_room, mock_routing):
        from chats.apps.sectors.models import SectorTag

        tag = SectorTag.objects.create(name="Tag A", sector=self.sector)
        room = Room.objects.create(queue=self.queue, contact=self.contact1, is_active=True)

        tags_map = {str(room.uuid): [str(tag.uuid)]}
        self.service.close(Room.objects.filter(pk=room.pk), room_tags_map=tags_map)

        room.refresh_from_db()
        self.assertFalse(room.is_active)
        self.assertIn(tag, room.tags.all())

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    @patch("chats.utils.websockets.send_channels_group")
    def test_rooms_with_no_queue_id_do_not_trigger_routing(self, mock_ws, mock_close_room, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact1, is_active=True
        )
        # Detach queue from room before closing
        Room.objects.filter(pk=room.pk).update(queue=None)
        room.refresh_from_db()

        self.service.close(Room.objects.filter(pk=room.pk))

        mock_routing.assert_not_called()
