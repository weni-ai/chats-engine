from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    BulkMessageSendStatus,
)
from chats.apps.msgs.usecases.update_bulk_message_send_progress import (
    UpdateBulkMessageSendProgressUseCase,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class UpdateBulkMessageSendProgressUseCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="requester@test.com",
            password="testpass123",
            first_name="Requester",
            last_name="User",
        )
        self.project = Project.objects.create(name="Test Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.bulk_send = BulkMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Bulk hello",
            filter_snapshot={},
            status=BulkMessageSendStatus.PROCESSING,
            rooms_qty=4,
        )
        self.usecase = UpdateBulkMessageSendProgressUseCase()

    def _create_room(self):
        return Room.objects.create(
            contact=Contact.objects.create(name="Contact"),
            queue=self.queue,
            is_active=True,
        )

    def _create_bulk_message(self, status):
        return BulkMessageSendMessage.objects.create(
            bulk_message_send=self.bulk_send,
            room=self._create_room(),
            message=None,
            status=status,
            errors={"error": "x"} if status == BulkMessageSendMessageStatus.FAILED else None,
        )

    @patch(
        "chats.apps.msgs.usecases.update_bulk_message_send_progress.send_channels_group"
    )
    def test_aggregates_counts_and_sends_ws_progress(self, mock_send):
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)
        self._create_bulk_message(BulkMessageSendMessageStatus.FAILED)

        content = self.usecase.execute(self.bulk_send.uuid)

        self.assertEqual(content["uuid"], str(self.bulk_send.uuid))
        self.assertEqual(content["success_total"], 2)
        self.assertEqual(content["failed_total"], 1)
        self.assertEqual(content["total_to_send"], 4)
        self.assertEqual(content["percentage"], 75.0)

        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.PROCESSING)

        mock_send.assert_called_once_with(
            group_name=f"permission_{self.permission.pk}",
            call_type="notify",
            action="bulk_message_progress_update",
            content={
                "uuid": str(self.bulk_send.uuid),
                "percentage": 75.0,
                "success_total": 2,
                "failed_total": 1,
                "total_to_send": 4,
            },
        )

    @patch(
        "chats.apps.msgs.usecases.update_bulk_message_send_progress.send_channels_group"
    )
    def test_marks_finished_at_100_percent(self, mock_send):
        for _ in range(3):
            self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)
        self._create_bulk_message(BulkMessageSendMessageStatus.FAILED)

        content = self.usecase.execute(self.bulk_send.uuid)

        self.assertEqual(content["percentage"], 100.0)
        self.assertEqual(content["success_total"], 3)
        self.assertEqual(content["failed_total"], 1)
        self.assertEqual(content["total_to_send"], 4)

        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.FINISHED)
        mock_send.assert_called_once()

    @patch(
        "chats.apps.msgs.usecases.update_bulk_message_send_progress.send_channels_group"
    )
    def test_percentage_rounded_to_two_decimals(self, mock_send):
        self.bulk_send.rooms_qty = 3
        self.bulk_send.save(update_fields=["rooms_qty"])
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)

        content = self.usecase.execute(self.bulk_send.uuid)

        self.assertEqual(content["percentage"], 33.33)
        mock_send.assert_called_once()

    @patch(
        "chats.apps.msgs.usecases.update_bulk_message_send_progress.send_channels_group"
    )
    def test_skips_ws_when_permission_missing(self, mock_send):
        self.permission.delete()
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)
        self._create_bulk_message(BulkMessageSendMessageStatus.SUCCESS)

        content = self.usecase.execute(self.bulk_send.uuid)

        self.assertEqual(content["percentage"], 100.0)
        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.FINISHED)
        mock_send.assert_not_called()

    @patch(
        "chats.apps.msgs.usecases.update_bulk_message_send_progress.send_channels_group"
    )
    def test_returns_none_when_bulk_send_missing(self, mock_send):
        result = self.usecase.execute(uuid4())

        self.assertIsNone(result)
        mock_send.assert_not_called()

    @patch(
        "chats.apps.msgs.usecases.update_bulk_message_send_progress.send_channels_group"
    )
    def test_zero_rooms_qty_does_not_finish(self, mock_send):
        self.bulk_send.rooms_qty = None
        self.bulk_send.save(update_fields=["rooms_qty"])

        content = self.usecase.execute(self.bulk_send.uuid)

        self.assertEqual(content["percentage"], 0.0)
        self.assertEqual(content["total_to_send"], 0)
        self.bulk_send.refresh_from_db()
        self.assertEqual(self.bulk_send.status, BulkMessageSendStatus.PROCESSING)
        mock_send.assert_called_once()
