from datetime import time
from unittest.mock import patch, MagicMock
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import (
    Project,
    ProjectPermission,
    RoomRoutingType,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.tasks import route_queue_rooms, route_sector_rooms
from chats.apps.sectors.models import Sector


FEATURE_FLAG_PATH = "chats.apps.queues.tasks.is_feature_active_for_attributes"


class RouteQueueRoomsTaskTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )

        self.agent = User.objects.create(
            email="agent@example.com",
            first_name="Test",
            last_name="Agent",
        )
        perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=perm,
            role=QueueAuthorization.ROLE_AGENT,
        )

        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("chats.apps.queues.tasks.logger")
    def test_returns_none_when_queue_not_found(self, mock_logger):
        fake_uuid = uuid4()
        result = route_queue_rooms(fake_uuid)

        self.assertIsNone(result)
        mock_logger.info.assert_any_call(
            "[route_queue_rooms] Queue not found for UUID: %s", fake_uuid
        )

    @patch(FEATURE_FLAG_PATH, return_value=False)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_routes_without_cooldown_when_feature_flag_is_off(
        self, mock_service_cls, mock_ff
    ):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        result = route_queue_rooms(self.queue.uuid)

        self.assertTrue(result)
        mock_service.route_rooms.assert_called_once()

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_acquires_lock_and_routes_when_cooldown_is_active(
        self, mock_service_cls, mock_ff
    ):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        result = route_queue_rooms(self.queue.uuid)

        self.assertTrue(result)
        mock_service.route_rooms.assert_called_once()

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_clears_lock_after_routing(self, mock_service_cls, mock_ff):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        route_queue_rooms(self.queue.uuid)

        lock_key = f"route_queue_rooms_lock:{self.sector.uuid}"
        self.assertIsNone(cache.get(lock_key))

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_clears_lock_even_when_routing_raises(self, mock_service_cls, mock_ff):
        mock_service = MagicMock()
        mock_service.route_rooms.side_effect = Exception("boom")
        mock_service_cls.return_value = mock_service

        with self.assertRaises(Exception):
            route_queue_rooms(self.queue.uuid)

        lock_key = f"route_queue_rooms_lock:{self.sector.uuid}"
        self.assertIsNone(cache.get(lock_key))


class RouteQueueRoomsCooldownTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Cooldown Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Cooldown Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Cooldown Queue",
            sector=self.sector,
        )

        cache.clear()

    def tearDown(self):
        cache.clear()

    def _lock_key(self, queue):
        return f"route_queue_rooms_lock:{queue.sector.uuid}"

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_rejected_call_schedules_deferred_retry(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        cache.set(self._lock_key(self.queue), True, timeout=30)

        result = route_queue_rooms(self.queue.uuid)

        self.assertFalse(result)
        mock_service_cls.assert_not_called()
        mock_apply_async.assert_called_once_with(
            args=[self.queue.uuid],
            countdown=2,
        )

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_second_rejected_call_does_not_schedule_duplicate_retry(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        cache.set(self._lock_key(self.queue), True, timeout=30)

        result_1 = route_queue_rooms(self.queue.uuid)
        result_2 = route_queue_rooms(self.queue.uuid)

        self.assertFalse(result_1)
        self.assertFalse(result_2)
        mock_service_cls.assert_not_called()
        mock_apply_async.assert_called_once()

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_multiple_rejected_calls_schedule_only_one_retry(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        cache.set(self._lock_key(self.queue), True, timeout=30)

        for _ in range(5):
            route_queue_rooms(self.queue.uuid)

        mock_apply_async.assert_called_once()

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_lock_is_cleared_after_successful_routing(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        route_queue_rooms(self.queue.uuid)

        self.assertIsNone(cache.get(self._lock_key(self.queue)))

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    @patch("chats.apps.queues.tasks.logger")
    def test_logs_when_cooldown_rejects_and_schedules_retry(
        self, mock_logger, mock_apply_async, mock_service_cls, mock_ff
    ):
        cache.set(self._lock_key(self.queue), True, timeout=30)

        route_queue_rooms(self.queue.uuid)

        mock_logger.info.assert_any_call(
            "[route_queue_rooms] Route queue rooms cooldown is active for queue %s. "
            "Skipping routing for now.",
            self.queue.uuid,
        )
        mock_logger.info.assert_any_call(
            "[route_queue_rooms] Scheduled deferred route_queue_rooms for queue %s",
            self.queue.uuid,
        )

    @override_settings(ROUTE_QUEUE_COOLDOWN_RETRY_DELAY=5)
    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_retry_uses_configured_delay(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        cache.set(self._lock_key(self.queue), True, timeout=30)

        route_queue_rooms(self.queue.uuid)

        mock_apply_async.assert_called_once_with(
            args=[self.queue.uuid],
            countdown=5,
        )

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_different_sectors_have_independent_locks(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        other_queue = Queue.objects.create(
            name="Other Queue",
            sector=other_sector,
        )

        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        cache.set(self._lock_key(self.queue), True, timeout=30)

        result_locked = route_queue_rooms(self.queue.uuid)
        result_unlocked = route_queue_rooms(other_queue.uuid)

        self.assertFalse(result_locked)
        self.assertTrue(result_unlocked)
        mock_service.route_rooms.assert_called_once()

    @patch(FEATURE_FLAG_PATH, return_value=True)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_queue_rooms.apply_async")
    def test_new_retry_can_be_scheduled_after_successful_routing_clears_lock(
        self, mock_apply_async, mock_service_cls, mock_ff
    ):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        route_queue_rooms(self.queue.uuid)

        self.assertIsNone(cache.get(self._lock_key(self.queue)))

        cache.set(self._lock_key(self.queue), True, timeout=30)

        route_queue_rooms(self.queue.uuid)

        mock_apply_async.assert_called_once_with(
            args=[self.queue.uuid],
            countdown=2,
        )


class RouteSectorRoomsTaskTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Sector Task Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Sector Task Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue_a = Queue.objects.create(
            name="Queue A",
            sector=self.sector,
        )
        self.queue_b = Queue.objects.create(
            name="Queue B",
            sector=self.sector,
        )

        cache.clear()

    def tearDown(self):
        cache.clear()

    def _lock_key(self):
        return f"route_queue_rooms_lock:{self.sector.uuid}"

    @patch("chats.apps.queues.tasks.logger")
    def test_returns_none_when_sector_not_found(self, mock_logger):
        fake_uuid = uuid4()
        result = route_sector_rooms(fake_uuid)

        self.assertIsNone(result)
        mock_logger.info.assert_any_call(
            "[route_sector_rooms] Sector not found for UUID: %s", fake_uuid
        )

    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_routes_all_queues_in_sector(self, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        result = route_sector_rooms(self.sector.uuid)

        self.assertTrue(result)
        self.assertEqual(mock_service.route_rooms.call_count, 2)

    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_acquires_and_releases_lock(self, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        route_sector_rooms(self.sector.uuid)

        self.assertIsNone(cache.get(self._lock_key()))

    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_clears_lock_even_when_routing_raises(self, mock_service_cls):
        mock_service = MagicMock()
        mock_service.route_rooms.side_effect = Exception("boom")
        mock_service_cls.return_value = mock_service

        with self.assertRaises(Exception):
            route_sector_rooms(self.sector.uuid)

        self.assertIsNone(cache.get(self._lock_key()))

    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_sector_rooms.apply_async")
    def test_rejected_call_schedules_deferred_retry(
        self, mock_apply_async, mock_service_cls
    ):
        cache.set(self._lock_key(), True, timeout=30)

        result = route_sector_rooms(self.sector.uuid)

        self.assertFalse(result)
        mock_service_cls.assert_not_called()
        mock_apply_async.assert_called_once_with(
            args=[self.sector.uuid],
            countdown=2,
        )

    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_sector_rooms.apply_async")
    def test_multiple_rejected_calls_schedule_only_one_retry(
        self, mock_apply_async, mock_service_cls
    ):
        cache.set(self._lock_key(), True, timeout=30)

        for _ in range(5):
            route_sector_rooms(self.sector.uuid)

        mock_apply_async.assert_called_once()

    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_sector_rooms.apply_async")
    def test_different_sectors_have_independent_locks(
        self, mock_apply_async, mock_service_cls
    ):
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        Queue.objects.create(name="Other Queue", sector=other_sector)

        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        cache.set(self._lock_key(), True, timeout=30)

        result_locked = route_sector_rooms(self.sector.uuid)
        result_unlocked = route_sector_rooms(other_sector.uuid)

        self.assertFalse(result_locked)
        self.assertTrue(result_unlocked)
        mock_service.route_rooms.assert_called_once()

    @patch("chats.apps.queues.tasks.QueueRouterService")
    def test_skips_queue_when_priority_routing_not_enabled(self, mock_service_cls):
        mock_service_cls.side_effect = ValueError("not enabled")

        result = route_sector_rooms(self.sector.uuid)

        self.assertTrue(result)

    @override_settings(ROUTE_QUEUE_COOLDOWN_RETRY_DELAY=7)
    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_sector_rooms.apply_async")
    def test_retry_uses_configured_delay(self, mock_apply_async, mock_service_cls):
        cache.set(self._lock_key(), True, timeout=30)

        route_sector_rooms(self.sector.uuid)

        mock_apply_async.assert_called_once_with(
            args=[self.sector.uuid],
            countdown=7,
        )

    @patch("chats.apps.queues.tasks.QueueRouterService")
    @patch("chats.apps.queues.tasks.route_sector_rooms.apply_async")
    @patch("chats.apps.queues.tasks.logger")
    def test_logs_when_cooldown_rejects_and_schedules_retry(
        self, mock_logger, mock_apply_async, mock_service_cls
    ):
        cache.set(self._lock_key(), True, timeout=30)

        route_sector_rooms(self.sector.uuid)

        mock_logger.info.assert_any_call(
            "[route_sector_rooms] Route sector rooms cooldown is active for sector %s. "
            "Skipping routing for now.",
            self.sector.uuid,
        )
        mock_logger.info.assert_any_call(
            "[route_sector_rooms] Scheduled deferred route_sector_rooms for sector %s",
            self.sector.uuid,
        )
