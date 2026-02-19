from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.rooms.services.bulk_close_service import BulkCloseService
from chats.apps.api.v1.rooms.services.bulk_transfer_service import BulkTransferService
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomPin
from chats.apps.sectors.models import Sector, SectorTag


class BulkTransferServiceTest(TestCase):
    def setUp(self):
        self.service = BulkTransferService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="test@test.com")
        self.room = Room.objects.create(queue=self.queue, user=self.user)
        self.rooms = Room.objects.filter(pk=self.room.pk)

        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def test_transfer_user_and_queue(self):
        user_2 = User.objects.create(email="test2@test.com")
        queue_2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        self.service.transfer_user_and_queue(self.rooms, user_2, queue_2, self.user)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, user_2)
        self.assertEqual(self.room.queue, queue_2)

    def test_transfer_user(self):
        user_2 = User.objects.create(email="test2@test.com")
        self.service.transfer_user(self.rooms, user_2, self.user)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, user_2)
        self.assertEqual(self.room.queue, self.queue)

    def test_transfer_queue(self):
        queue_2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        self.service.transfer_queue(self.rooms, queue_2, self.user)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, None)
        self.assertEqual(self.room.queue, queue_2)

    def test_validate_queue(self):
        self.service.validate_queue(self.rooms, self.queue)

    def test_validate_queue_when_queue_is_from_another_project(self):
        queue_2 = Queue.objects.create(
            name="Test Queue 2",
            sector=Sector.objects.create(
                name="Test Sector 2",
                project=Project.objects.create(name="Test Project 2"),
                rooms_limit=10,
                work_start="09:00",
                work_end="18:00",
            ),
        )

        with self.assertRaises(ValueError) as context:
            self.service.validate_queue(self.rooms, queue_2)

        self.assertEqual(
            str(context.exception), "Cannot transfer rooms from a project to another"
        )

    def test_validate_user(self):
        self.service.validate_user(self.rooms, self.user)

    def test_validate_user_when_user_has_no_permission_on_project(self):
        user_2 = User.objects.create(email="test2@test.com")

        with self.assertRaises(ValueError) as context:
            self.service.validate_user(self.rooms, user_2)

        self.assertEqual(
            str(context.exception), "User has no permission on the project"
        )


class BulkCloseServiceTest(TestCase):
    def setUp(self):
        self.service = BulkCloseService()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            is_csat_enabled=False,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="test@test.com")

        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def test_close_single_room(self):
        """Test closing a single room via room.close()"""
        room = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        rooms = Room.objects.filter(pk=room.pk)

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)
        room.refresh_from_db()
        self.assertFalse(room.is_active)
        self.assertIsNotNone(room.ended_at)

    def test_close_multiple_rooms(self):
        """Test closing multiple rooms"""
        rooms_objs = [
            Room.objects.create(queue=self.queue, user=self.user, is_active=True)
            for _ in range(10)
        ]
        room_ids = [room.pk for room in rooms_objs]
        rooms = Room.objects.filter(pk__in=room_ids)

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 10)
        self.assertEqual(result.failed_count, 0)
        for room in Room.objects.filter(pk__in=room_ids):
            self.assertFalse(room.is_active)
            self.assertIsNotNone(room.ended_at)

    def test_close_with_end_by_and_closed_by(self):
        """Test that end_by and closed_by are passed to room.close()"""
        room = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        closer_user = User.objects.create(email="closer@test.com")
        rooms = Room.objects.filter(pk=room.pk)

        result = self.service.close(
            rooms,
            end_by="agent",
            closed_by=closer_user,
        )

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)
        room.refresh_from_db()
        self.assertEqual(room.ended_by, "agent")
        self.assertEqual(room.closed_by, closer_user)

    def test_close_with_tags(self):
        """Test that tags are forwarded to room.close()"""
        room = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        tag1 = SectorTag.objects.create(name="Tag1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag2", sector=self.sector)
        rooms = Room.objects.filter(pk=room.pk)

        room_tags_map = {
            str(room.uuid): [str(tag1.uuid), str(tag2.uuid)]
        }

        result = self.service.close(rooms, room_tags_map=room_tags_map)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 0)
        room.refresh_from_db()
        self.assertFalse(room.is_active)
        self.assertEqual(room.tags.count(), 2)
        self.assertIn(tag1, room.tags.all())
        self.assertIn(tag2, room.tags.all())

    def test_close_clears_pins(self):
        """Test that room.close() clears pins for each room"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)

        RoomPin.objects.create(room=room1, user=self.user)
        RoomPin.objects.create(room=room2, user=self.user)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])
        self.assertEqual(RoomPin.objects.filter(room__in=rooms).count(), 2)

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(RoomPin.objects.filter(room__in=rooms).count(), 0)

    def test_close_tracks_already_closed_rooms_as_failures(self):
        """Test that already-closed rooms are recorded as failures"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=False)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertIn(str(room2.uuid), result.failed_rooms)

    def test_close_returns_empty_result_for_empty_queryset(self):
        """Test that an empty queryset returns a zero-count result"""
        rooms = Room.objects.none()

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 0)

    def test_close_rooms_in_queue(self):
        """Test closing rooms in queue (no user assigned)"""
        room1 = Room.objects.create(queue=self.queue, user=None, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=None, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)
        for room in [room1, room2]:
            room.refresh_from_db()
            self.assertFalse(room.is_active)

    def test_close_rooms_in_progress(self):
        """Test closing rooms in progress (user assigned)"""
        user1 = User.objects.create(email="agent1@test.com")
        user2 = User.objects.create(email="agent2@test.com")
        room1 = Room.objects.create(queue=self.queue, user=user1, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=user2, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)
        for room in [room1, room2]:
            room.refresh_from_db()
            self.assertFalse(room.is_active)

    def test_close_updates_ended_at_timestamp(self):
        """Test that ended_at is set by room.close()"""
        room = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        rooms = Room.objects.filter(pk=room.pk)

        before_close = timezone.now()
        result = self.service.close(rooms)
        after_close = timezone.now()

        self.assertEqual(result.success_count, 1)
        room.refresh_from_db()
        self.assertIsNotNone(room.ended_at)
        self.assertGreaterEqual(room.ended_at, before_close)
        self.assertLessEqual(room.ended_at, after_close)

    @patch("chats.apps.projects.usecases.status_service.InServiceStatusService.room_closed")
    def test_close_calls_inservice_status_update(self, mock_room_closed):
        """Test that room.close() triggers InService status update"""
        room = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        rooms = Room.objects.filter(pk=room.pk)

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 1)
        mock_room_closed.assert_called_once_with(self.user, self.project)

    def test_close_tracks_individual_failures(self):
        """Test that individual failures are tracked with details"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=False)
        room3 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk, room3.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(len(result.failed_rooms), 1)
        self.assertIn(str(room2.uuid), result.failed_rooms)

    def test_close_result_to_dict(self):
        """Test that BulkCloseResult.to_dict() returns correct structure"""
        room = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        rooms = Room.objects.filter(pk=room.pk)

        result = self.service.close(rooms)
        result_dict = result.to_dict()

        self.assertIn("success_count", result_dict)
        self.assertIn("failed_count", result_dict)
        self.assertIn("total_processed", result_dict)
        self.assertIn("errors", result_dict)
        self.assertIn("failed_rooms", result_dict)
        self.assertIn("has_more_errors", result_dict)
        self.assertEqual(result_dict["total_processed"], 1)

    def test_close_with_different_tags_per_room(self):
        """Test closing rooms with different tags for each"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room3 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)

        tag1 = SectorTag.objects.create(name="Tag1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag2", sector=self.sector)
        tag3 = SectorTag.objects.create(name="Tag3", sector=self.sector)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk, room3.pk])

        room_tags_map = {
            str(room1.uuid): [str(tag1.uuid)],
            str(room2.uuid): [str(tag2.uuid), str(tag3.uuid)],
            str(room3.uuid): [],
        }

        result = self.service.close(rooms, room_tags_map=room_tags_map)

        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.failed_count, 0)

        room1.refresh_from_db()
        room2.refresh_from_db()
        room3.refresh_from_db()

        self.assertEqual(room1.tags.count(), 1)
        self.assertIn(tag1, room1.tags.all())

        self.assertEqual(room2.tags.count(), 2)
        self.assertIn(tag2, room2.tags.all())
        self.assertIn(tag3, room2.tags.all())

        self.assertEqual(room3.tags.count(), 0)

    def test_close_multiple_sectors_with_different_tags(self):
        """Test closing rooms from different sectors with sector-specific tags"""
        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            is_csat_enabled=False,
        )
        queue2 = Queue.objects.create(name="Test Queue 2", sector=sector2)

        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=queue2, user=self.user, is_active=True)

        tag1 = SectorTag.objects.create(name="Sector1Tag", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Sector2Tag", sector=sector2)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        room_tags_map = {
            str(room1.uuid): [str(tag1.uuid)],
            str(room2.uuid): [str(tag2.uuid)],
        }

        result = self.service.close(rooms, room_tags_map=room_tags_map)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)

        room1.refresh_from_db()
        room2.refresh_from_db()

        self.assertEqual(room1.tags.count(), 1)
        self.assertIn(tag1, room1.tags.all())

        self.assertEqual(room2.tags.count(), 1)
        self.assertIn(tag2, room2.tags.all())

    @override_settings(BULK_CLOSE_BATCH_SIZE=3)
    def test_close_processes_rooms_across_multiple_batches(self):
        """Test that rooms are split across batches correctly"""
        rooms_objs = [
            Room.objects.create(queue=self.queue, user=self.user, is_active=True)
            for _ in range(7)
        ]
        room_ids = [room.pk for room in rooms_objs]
        rooms = Room.objects.filter(pk__in=room_ids)

        result = self.service.close(rooms)

        # All 7 rooms closed despite batch_size=3 (3 batches: 3+3+1)
        self.assertEqual(result.success_count, 7)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(
            Room.objects.filter(pk__in=room_ids, is_active=True).count(), 0
        )

    @override_settings(BULK_CLOSE_BATCH_SIZE=2)
    def test_close_batch_failures_dont_stop_other_batches(self):
        """Test that a failure in one batch does not prevent the next batch"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=False)
        room3 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room4 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk, room3.pk, room4.pk])

        result = self.service.close(rooms)

        # room2 fails, the rest succeed across batches
        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.failed_count, 1)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.close_room")
    def test_close_calls_close_room_for_metrics(self, mock_close_room):
        """Test that close_room() is called for each successfully closed room"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(mock_close_room.call_count, 2)
        mock_close_room.assert_any_call(str(room1.uuid))
        mock_close_room.assert_any_call(str(room2.uuid))

    @patch("chats.apps.rooms.models.Room.notify_queue")
    def test_close_sends_notify_queue_for_all_rooms(self, mock_notify_queue):
        """Test that notify_queue('close', callback=True) is called for every closed room"""
        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=None, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(mock_notify_queue.call_count, 2)
        mock_notify_queue.assert_any_call("close", callback=True)

    @patch("chats.apps.rooms.models.Room.notify_user")
    @patch("chats.apps.rooms.models.Room.notify_queue")
    def test_close_sends_notify_user_only_for_rooms_in_progress(
        self, mock_notify_queue, mock_notify_user
    ):
        """Test that notify_user('close') is called only for rooms with a user assigned"""
        room_in_progress = Room.objects.create(
            queue=self.queue, user=self.user, is_active=True
        )
        room_in_queue = Room.objects.create(
            queue=self.queue, user=None, is_active=True
        )

        rooms = Room.objects.filter(pk__in=[room_in_progress.pk, room_in_queue.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        # notify_queue called for both
        self.assertEqual(mock_notify_queue.call_count, 2)
        # notify_user called only for the room with a user
        self.assertEqual(mock_notify_user.call_count, 1)
        mock_notify_user.assert_called_once_with("close")

    @patch("chats.apps.rooms.models.Room.notify_user")
    @patch("chats.apps.rooms.models.Room.notify_queue")
    def test_close_does_not_send_notify_user_for_queued_rooms(
        self, mock_notify_queue, mock_notify_user
    ):
        """Test that notify_user is NOT called for rooms in queue (user=None)"""
        room1 = Room.objects.create(queue=self.queue, user=None, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=None, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(mock_notify_queue.call_count, 2)
        self.assertEqual(mock_notify_user.call_count, 0)

    @patch("chats.apps.api.v1.rooms.services.bulk_close_service.start_queue_priority_routing")
    def test_close_triggers_routing_once_per_unique_queue(self, mock_start_routing):
        """Test that start_queue_priority_routing is called once per unique queue"""
        queue2 = Queue.objects.create(name="Queue 2", sector=self.sector)

        room1 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room2 = Room.objects.create(queue=self.queue, user=self.user, is_active=True)
        room3 = Room.objects.create(queue=queue2, user=self.user, is_active=True)

        rooms = Room.objects.filter(pk__in=[room1.pk, room2.pk, room3.pk])

        result = self.service.close(rooms)

        self.assertEqual(result.success_count, 3)
        # Called once per unique queue (2 queues)
        self.assertEqual(mock_start_routing.call_count, 2)
