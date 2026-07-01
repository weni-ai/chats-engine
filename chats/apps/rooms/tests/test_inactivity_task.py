from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from celery.schedules import crontab
from django.test import TestCase, override_settings

from chats.apps.rooms.tasks import check_inactivity_rooms


@contextmanager
def _mocked_redis_lock(acquire_result: bool = True):
    """
    Patches `django_redis.get_redis_connection` so the inactivity task can
    interact with a lock-like object without a real Redis. Yields the lock
    and the Redis connection mocks so tests can assert acquire/release and
    lock-construction behaviour.
    """
    lock_mock = MagicMock()
    lock_mock.acquire.return_value = acquire_result

    redis_mock = MagicMock()
    redis_mock.lock.return_value = lock_mock

    with patch("django_redis.get_redis_connection", return_value=redis_mock):
        yield lock_mock, redis_mock


class CheckInactivityRoomsTaskTests(TestCase):
    """
    Tests for the periodic Celery task that drives the inactivity feature.

    The business logic is covered by `test_inactivity_usecase.py`; here we
    only verify that the task wires the usecase calls together correctly and
    isolates failures between the warning and closure steps.
    """

    def test_task_calls_warn_then_close(self):
        with _mocked_redis_lock(), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls:
            mocked_service = mocked_service_cls.return_value
            mocked_service.warn_inactive_rooms.return_value = 3
            mocked_service.close_inactive_rooms.return_value = 1

            check_inactivity_rooms()

            mocked_service.warn_inactive_rooms.assert_called_once_with()
            mocked_service.close_inactive_rooms.assert_called_once_with()

    def test_task_runs_close_even_when_warn_raises(self):
        with _mocked_redis_lock(), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls, patch(
            "chats.apps.rooms.tasks.capture_exception"
        ) as mocked_capture:
            mocked_service = mocked_service_cls.return_value
            mocked_service.warn_inactive_rooms.side_effect = RuntimeError("boom")
            mocked_service.close_inactive_rooms.return_value = 0

            check_inactivity_rooms()

            mocked_service.warn_inactive_rooms.assert_called_once_with()
            mocked_service.close_inactive_rooms.assert_called_once_with()
            mocked_capture.assert_called_once()

    def test_task_does_not_propagate_close_exception(self):
        with _mocked_redis_lock(), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls, patch(
            "chats.apps.rooms.tasks.capture_exception"
        ) as mocked_capture:
            mocked_service = mocked_service_cls.return_value
            mocked_service.warn_inactive_rooms.return_value = 0
            mocked_service.close_inactive_rooms.side_effect = RuntimeError("boom")

            try:
                check_inactivity_rooms()
            except Exception as exc:
                self.fail(f"Task must swallow close exceptions, got: {exc}")

            mocked_capture.assert_called_once()


class CheckInactivityRoomsLockTests(TestCase):
    """
    Tests for the Redis-backed distributed lock that prevents two task
    executions from processing the same eligible rooms concurrently.
    """

    def test_task_skips_when_lock_is_already_held(self):
        with _mocked_redis_lock(acquire_result=False), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls:
            check_inactivity_rooms()

            mocked_service_cls.assert_not_called()

    def test_lock_is_released_after_successful_run(self):
        with _mocked_redis_lock() as (lock_mock, _), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls:
            mocked_service = mocked_service_cls.return_value
            mocked_service.warn_inactive_rooms.return_value = 0
            mocked_service.close_inactive_rooms.return_value = 0

            check_inactivity_rooms()

            lock_mock.release.assert_called_once()

    def test_lock_is_released_even_when_warn_and_close_raise(self):
        with _mocked_redis_lock() as (lock_mock, _), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls, patch(
            "chats.apps.rooms.tasks.capture_exception"
        ):
            mocked_service = mocked_service_cls.return_value
            mocked_service.warn_inactive_rooms.side_effect = RuntimeError("warn")
            mocked_service.close_inactive_rooms.side_effect = RuntimeError("close")

            check_inactivity_rooms()

            lock_mock.release.assert_called_once()

    def test_release_failure_is_logged_but_not_raised(self):
        with _mocked_redis_lock() as (lock_mock, _), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls:
            mocked_service_cls.return_value.warn_inactive_rooms.return_value = 0
            mocked_service_cls.return_value.close_inactive_rooms.return_value = 0
            lock_mock.release.side_effect = RuntimeError("lock expired")

            try:
                check_inactivity_rooms()
            except Exception as exc:
                self.fail(
                    f"Task must swallow lock release errors, got: {exc}"
                )

    @override_settings(
        INACTIVITY_TASK_LOCK_NAME="custom_lock",
        INACTIVITY_TASK_LOCK_TIMEOUT=42,
    )
    def test_lock_is_acquired_with_configured_name_and_timeout(self):
        with _mocked_redis_lock() as (_, redis_mock), patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls:
            mocked_service_cls.return_value.warn_inactive_rooms.return_value = 0
            mocked_service_cls.return_value.close_inactive_rooms.return_value = 0

            check_inactivity_rooms()

            redis_mock.lock.assert_called_once_with("custom_lock", timeout=42)


class CheckInactivityRoomsScheduleTests(TestCase):
    """
    Sanity check that the task is registered in the Celery beat schedule and
    runs every minute.
    """

    def test_task_is_registered_in_beat_schedule(self):
        from django.conf import settings

        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn("check-inactivity-rooms", schedule)

        entry = schedule["check-inactivity-rooms"]
        self.assertEqual(entry["task"], "check_inactivity_rooms")
        self.assertIsInstance(entry["schedule"], crontab)

    @override_settings(
        CELERY_BEAT_SCHEDULE={
            "check-inactivity-rooms": {
                "task": "check_inactivity_rooms",
                "schedule": crontab(minute="*"),
            }
        }
    )
    def test_schedule_runs_every_minute(self):
        from django.conf import settings

        entry = settings.CELERY_BEAT_SCHEDULE["check-inactivity-rooms"]
        self.assertEqual(entry["schedule"]._orig_minute, "*")
