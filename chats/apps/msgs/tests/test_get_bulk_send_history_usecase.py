from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    BulkMessageSendStatus,
)
from chats.apps.msgs.usecases.get_bulk_send_history import GetBulkSendHistoryUseCase
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class GetBulkSendHistoryUseCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sender@test.com",
            password="testpass123",
            first_name="Sender",
        )
        self.other_user = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            first_name="Other",
        )
        self.project = Project.objects.create(name="Test Project")
        self.other_project = Project.objects.create(name="Other Project")

        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)

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

        self.usecase = GetBulkSendHistoryUseCase()

    def _create_bulk_message(
        self,
        *,
        user=None,
        project=None,
        queue=None,
        contact_name="Contact",
        status_value=BulkMessageSendMessageStatus.SUCCESS,
        created_on=None,
    ) -> BulkMessageSendMessage:
        bulk_send = BulkMessageSend.objects.create(
            user=user or self.user,
            project=project or self.project,
            text="Bulk hello",
            status=BulkMessageSendStatus.FINISHED,
        )
        room = Room.objects.create(
            contact=Contact.objects.create(name=contact_name),
            queue=queue or self.queue,
        )
        bulk_message = BulkMessageSendMessage.objects.create(
            bulk_message_send=bulk_send,
            room=room,
            status=status_value,
        )
        if created_on is not None:
            BulkMessageSendMessage.objects.filter(uuid=bulk_message.uuid).update(
                created_on=created_on
            )
            bulk_message.refresh_from_db()
        return bulk_message

    def test_returns_only_messages_from_the_given_project(self):
        in_project = self._create_bulk_message(contact_name="In Project")
        self._create_bulk_message(
            project=self.other_project,
            queue=self.other_queue,
            contact_name="Other Project",
        )

        result = list(self.usecase.execute(self.project.uuid))

        self.assertEqual(result, [in_project])

    def test_filters_by_start_and_end_date(self):
        today = timezone.now()
        older = self._create_bulk_message(
            contact_name="Older",
            created_on=today - timedelta(days=5),
        )
        recent = self._create_bulk_message(
            contact_name="Recent",
            created_on=today - timedelta(days=1),
        )

        result = list(
            self.usecase.execute(
                self.project.uuid,
                {
                    "start_date": (today - timedelta(days=2)).date(),
                    "end_date": date.today(),
                },
            )
        )

        self.assertEqual(result, [recent])
        self.assertNotIn(older, result)

    def test_filters_by_sender(self):
        from_sender = self._create_bulk_message(user=self.user, contact_name="Mine")
        self._create_bulk_message(user=self.other_user, contact_name="Theirs")

        result = list(
            self.usecase.execute(
                self.project.uuid,
                {"sender": self.user.email},
            )
        )

        self.assertEqual(result, [from_sender])

    def test_filters_by_status(self):
        success = self._create_bulk_message(
            contact_name="Success",
            status_value=BulkMessageSendMessageStatus.SUCCESS,
        )
        self._create_bulk_message(
            contact_name="Failed",
            status_value=BulkMessageSendMessageStatus.FAILED,
        )

        result = list(
            self.usecase.execute(
                self.project.uuid,
                {"status": BulkMessageSendMessageStatus.SUCCESS},
            )
        )

        self.assertEqual(result, [success])

    def test_orders_by_created_on_descending(self):
        older = self._create_bulk_message(
            contact_name="Older",
            created_on=timezone.now() - timedelta(days=2),
        )
        newer = self._create_bulk_message(
            contact_name="Newer",
            created_on=timezone.now() - timedelta(days=1),
        )

        result = list(self.usecase.execute(self.project.uuid))

        self.assertEqual(result, [newer, older])
