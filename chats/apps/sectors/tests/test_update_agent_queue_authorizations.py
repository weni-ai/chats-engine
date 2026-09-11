from uuid import uuid4

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import GroupSector, Sector
from chats.apps.sectors.usecases.group_sector_authorization import (
    UpdateAgentQueueAuthorizationsUseCase,
)


class UpdateAgentQueueAuthorizationsUseCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="agent@test.com", password="pw")
        self.project = Project.objects.create(name="Auth Project")
        self.other_project = Project.objects.create(name="Other")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.group_sector = GroupSector.objects.create(
            name="Group", project=self.project, rooms_limit=5
        )
        self.group_sector.sectors.add(self.sector)
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    def test_raises_when_group_sector_does_not_exist(self):
        with self.assertRaises(ValueError):
            UpdateAgentQueueAuthorizationsUseCase(
                group_sector_uuid=uuid4(),
                permission_uuid=self.permission.uuid,
            )

    def test_raises_when_permission_is_from_another_project(self):
        other_permission = ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        with self.assertRaises(ValueError) as context:
            UpdateAgentQueueAuthorizationsUseCase(
                group_sector_uuid=self.group_sector.uuid,
                permission_uuid=other_permission.uuid,
            )
        self.assertIn("does not belong", str(context.exception))

    def test_enables_allowed_queue_and_ignores_unknown_uuid(self):
        use_case = UpdateAgentQueueAuthorizationsUseCase(
            group_sector_uuid=self.group_sector.uuid,
            permission_uuid=self.permission.uuid,
            enabled_queue_uuids=[self.queue.uuid, uuid4()],
        )
        use_case.execute()

        self.assertTrue(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=self.queue
            ).exists()
        )

    def test_disables_existing_authorization(self):
        QueueAuthorization.objects.create(
            queue=self.queue, permission=self.permission, role=1
        )
        use_case = UpdateAgentQueueAuthorizationsUseCase(
            group_sector_uuid=self.group_sector.uuid,
            permission_uuid=self.permission.uuid,
            disabled_queue_uuids=[self.queue.uuid],
        )
        use_case.execute()

        self.assertFalse(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=self.queue
            ).exists()
        )
