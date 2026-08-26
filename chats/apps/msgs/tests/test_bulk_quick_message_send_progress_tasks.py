from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from chats.apps.msgs.models import BulkQuickMessageSend, BulkQuickMessageSendStatus
from chats.apps.msgs.tasks import finish_stale_bulk_quick_message_sends
from chats.apps.projects.models import Project

User = get_user_model()


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
