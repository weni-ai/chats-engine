from django.test import TestCase

from chats.apps.api.v1.rooms.services.bulk_transfer_service import BulkTransferService
from chats.apps.projects.models.models import Project, ProjectPermission
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
        self.rooms = Room.objects.filter(pk=self.room.pk)

        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def test_transfer_user_and_queue(self):
        user_2 = User.objects.create(email="test2@test.com")
        queue_2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        self.service.transfer_user_and_queue(self.rooms, user_2, queue_2)

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
