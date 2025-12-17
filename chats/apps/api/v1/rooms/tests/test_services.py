from django.test import TestCase

from chats.apps.api.v1.rooms.services.bulk_transfer_service import BulkTransferService
from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.accounts.models import User
from chats.apps.rooms.models import Room


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

    def test_transfer_user_and_queue(self):
        user_2 = User.objects.create(email="test2@test.com")
        queue_2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        self.service.transfer_user_and_queue([self.room], user_2, queue_2)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, user_2)
        self.assertEqual(self.room.queue, queue_2)

    def test_transfer_user(self):
        user_2 = User.objects.create(email="test2@test.com")
        self.service.transfer_user([self.room], user_2, self.user)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, user_2)
        self.assertEqual(self.room.queue, self.queue)

    def test_transfer_queue(self):
        queue_2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        self.service.transfer_queue([self.room], queue_2, self.user)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, None)
        self.assertEqual(self.room.queue, queue_2)
