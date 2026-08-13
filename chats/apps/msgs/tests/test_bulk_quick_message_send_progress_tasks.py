from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from chats.apps.msgs.models import BulkQuickMessageSend, BulkQuickMessageSendStatus
from chats.apps.msgs.tasks import (
    finish_stale_bulk_quick_message_sends,
    get_bulk_quick_send_progress_lock_key,
    update_bulk_quick_message_send_progress,
)
from chats.apps.projects.models import Project

User = get_user_model()


class UpdateBulkQuickMessageSendProgressTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="attendant@test.com",
            password="testpass123",
        )
        self.project = Project.objects.create(name="Test Project")
        self.bulk_send = BulkQuickMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Quick hello",
            contacts=None,
            status=BulkQuickMessageSendStatus.PROCESSING,
            rooms_qty=2,
        )
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _lock_key(self):
        return get_bulk_quick_send_progress_lock_key(self.bulk_send.uuid)

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress_usecase")
    def test_acquires_lock_and_updates_progress(self, mock_usecase):
        result = update_bulk_quick_message_send_progress(self.bulk_send.uuid)

        self.assertTrue(result)
        mock_usecase.execute.assert_called_once_with(self.bulk_send.uuid)
        self.assertTrue(cache.get(self._lock_key()))

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress_usecase")
    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.apply_async")
    def test_rejected_call_schedules_deferred_retry(
        self, mock_apply_async, mock_usecase
    ):
        cache.set(self._lock_key(), True, timeout=30)

        result = update_bulk_quick_message_send_progress(self.bulk_send.uuid)

        self.assertFalse(result)
        mock_usecase.execute.assert_not_called()
        mock_apply_async.assert_called_once_with(
            args=[self.bulk_send.uuid],
            countdown=1,
        )

    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress_usecase")
    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.apply_async")
    def test_second_rejected_call_does_not_schedule_duplicate_retry(
        self, mock_apply_async, mock_usecase
    ):
        cache.set(self._lock_key(), True, timeout=30)

        result_1 = update_bulk_quick_message_send_progress(self.bulk_send.uuid)
        result_2 = update_bulk_quick_message_send_progress(self.bulk_send.uuid)

        self.assertFalse(result_1)
        self.assertFalse(result_2)
        mock_usecase.execute.assert_not_called()
        mock_apply_async.assert_called_once()

    @override_settings(BULK_SEND_PROGRESS_RETRY_DELAY=5)
    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress_usecase")
    @patch("chats.apps.msgs.tasks.update_bulk_quick_message_send_progress.apply_async")
    def test_retry_uses_configured_delay(self, mock_apply_async, mock_usecase):
        cache.set(self._lock_key(), True, timeout=30)

        update_bulk_quick_message_send_progress(self.bulk_send.uuid)

        mock_apply_async.assert_called_once_with(
            args=[self.bulk_send.uuid],
            countdown=5,
        )


class FinishStaleBulkQuickMessageSendsTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="attendant@test.com",
            password="testpass123",
        )
        self.project = Project.objects.create(name="Test Project")

    def _create_bulk_send(self, status, created_on):
        bulk_send = BulkQuickMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Quick hello",
            contacts=None,
            status=status,
            rooms_qty=1,
        )
        BulkQuickMessageSend.objects.filter(pk=bulk_send.pk).update(
            created_on=created_on
        )
        bulk_send.refresh_from_db()
        return bulk_send

    @override_settings(BULK_SEND_STALE_FINISH_MINUTES=30)
    def test_marks_stale_non_finished_as_finished(self):
        stale = self._create_bulk_send(
            BulkQuickMessageSendStatus.PROCESSING,
            timezone.now() - timedelta(minutes=31),
        )
        recent = self._create_bulk_send(
            BulkQuickMessageSendStatus.PROCESSING,
            timezone.now() - timedelta(minutes=10),
        )
        already_finished = self._create_bulk_send(
            BulkQuickMessageSendStatus.FINISHED,
            timezone.now() - timedelta(minutes=60),
        )

        updated = finish_stale_bulk_quick_message_sends()

        self.assertEqual(updated, 1)
        stale.refresh_from_db()
        recent.refresh_from_db()
        already_finished.refresh_from_db()
        self.assertEqual(stale.status, BulkQuickMessageSendStatus.FINISHED)
        self.assertEqual(recent.status, BulkQuickMessageSendStatus.PROCESSING)
        self.assertEqual(
            already_finished.status, BulkQuickMessageSendStatus.FINISHED
        )

    @override_settings(BULK_SEND_STALE_FINISH_MINUTES=30)
    def test_marks_stale_pending_as_finished(self):
        stale = self._create_bulk_send(
            BulkQuickMessageSendStatus.PENDING,
            timezone.now() - timedelta(minutes=45),
        )

        updated = finish_stale_bulk_quick_message_sends()

        self.assertEqual(updated, 1)
        stale.refresh_from_db()
        self.assertEqual(stale.status, BulkQuickMessageSendStatus.FINISHED)
