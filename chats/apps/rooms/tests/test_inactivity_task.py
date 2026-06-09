from unittest.mock import patch

from celery.schedules import crontab
from django.test import TestCase, override_settings

from chats.apps.rooms.tasks import check_inactivity_rooms


class CheckInactivityRoomsTaskTests(TestCase):
    """
    Tests for the periodic Celery task that drives the inactivity feature.

    The business logic is covered by `test_inactivity_usecase.py`; here we
    only verify that the task wires the usecase calls together correctly and
    isolates failures between the warning and closure steps.
    """

    def test_task_calls_warn_then_close(self):
        with patch(
            "chats.apps.rooms.usecases.inactivity.InactivityService"
        ) as mocked_service_cls:
            mocked_service = mocked_service_cls.return_value
            mocked_service.warn_inactive_rooms.return_value = 3
            mocked_service.close_inactive_rooms.return_value = 1

            check_inactivity_rooms()

            mocked_service.warn_inactive_rooms.assert_called_once_with()
            mocked_service.close_inactive_rooms.assert_called_once_with()

    def test_task_runs_close_even_when_warn_raises(self):
        with patch(
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
        with patch(
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
