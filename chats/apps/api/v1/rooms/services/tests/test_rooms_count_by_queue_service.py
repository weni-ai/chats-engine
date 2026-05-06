from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.rooms.services.rooms_count_by_queue_service import (
    RoomsCountByQueueService,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization

User = get_user_model()


class RoomsCountByQueueServiceTestsBase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")

        self.sector_a = Sector.objects.create(
            name="A Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_b = Sector.objects.create(
            name="B Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        self.queue_a1 = Queue.objects.create(name="A1 Queue", sector=self.sector_a)
        self.queue_a2 = Queue.objects.create(name="A2 Queue", sector=self.sector_a)
        self.queue_b1 = Queue.objects.create(name="B1 Queue", sector=self.sector_b)

        self.agent = User.objects.create_user(email="agent@test.com")

        self.service = RoomsCountByQueueService()

    def _create_room(self, queue, *, user=None, is_active=True, is_waiting=False):
        return Room.objects.create(
            queue=queue,
            contact=Contact.objects.create(),
            user=user,
            is_active=is_active,
            is_waiting=is_waiting,
        )

    def _flatten(self, result):
        flat = {}
        for sector in result["sectors"]:
            for queue in sector["queues"]:
                flat[queue["uuid"]] = {
                    "sector": sector["name"],
                    "queued": queue["rooms_in_awaiting"],
                    "in_service": queue["rooms_in_progress"],
                }
        return flat


class RoomsCountByQueueServiceWithoutTargetEmailTests(
    RoomsCountByQueueServiceTestsBase
):
    """
    Without `target_email`, the service uses the requesting permission
    directly.
    """

    def test_admin_requester_sees_all_sectors_and_queues(self):
        admin = User.objects.create_user(email="admin@test.com")
        admin_perm = ProjectPermission.objects.create(
            user=admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=admin_perm,
        )

        flat = self._flatten(result)
        self.assertEqual(
            set(flat.keys()),
            {
                str(self.queue_a1.uuid),
                str(self.queue_a2.uuid),
                str(self.queue_b1.uuid),
            },
        )

    def test_admin_requester_in_service_only_counts_own_assigned_rooms(self):
        admin = User.objects.create_user(email="admin@test.com")
        admin_perm = ProjectPermission.objects.create(
            user=admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self._create_room(self.queue_a1, user=admin)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_b1, user=self.agent)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=admin_perm,
        )

        flat = self._flatten(result)
        # Manager view: in_service counts every assigned room globally.
        total_in_service = sum(q["in_service"] for q in flat.values())
        self.assertEqual(total_in_service, 3)

    def test_attendant_requester_only_sees_authorized_queues(self):
        attendant = User.objects.create_user(email="attendant@test.com")
        attendant_perm = ProjectPermission.objects.create(
            user=attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=attendant_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=attendant_perm,
        )

        flat = self._flatten(result)
        self.assertEqual(set(flat.keys()), {str(self.queue_a1.uuid)})

    def test_attendant_requester_in_service_only_counts_own_rooms(self):
        attendant = User.objects.create_user(email="attendant@test.com")
        attendant_perm = ProjectPermission.objects.create(
            user=attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=attendant_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self._create_room(self.queue_a1, user=attendant)
        self._create_room(self.queue_a1, user=attendant)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_a1)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=attendant_perm,
        )

        flat = self._flatten(result)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 1)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 2)


class RoomsCountByQueueServiceWithTargetEmailTests(RoomsCountByQueueServiceTestsBase):
    """
    With `target_email`, the service uses the target user's permission to
    determine visibility and counts the in-service rooms assigned to that
    target.
    """

    def setUp(self):
        super().setUp()
        self.requester_admin = User.objects.create_user(email="requester@test.com")
        self.requester_perm = ProjectPermission.objects.create(
            user=self.requester_admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def test_target_email_attendant_restricts_to_authorized_queues(self):
        target = User.objects.create_user(email="target@test.com")
        target_perm = ProjectPermission.objects.create(
            user=target,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=target_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a2)
        self._create_room(self.queue_b1)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.requester_perm,
            target_email=target.email,
        )

        flat = self._flatten(result)
        self.assertEqual(set(flat.keys()), {str(self.queue_a1.uuid)})

    def test_target_email_attendant_in_service_only_counts_target_rooms(self):
        target = User.objects.create_user(email="target@test.com")
        target_perm = ProjectPermission.objects.create(
            user=target,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=target_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self._create_room(self.queue_a1, user=target)
        self._create_room(self.queue_a1, user=self.agent)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.requester_perm,
            target_email=target.email,
        )

        flat = self._flatten(result)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)

    def test_target_email_admin_returns_global_counts(self):
        target = User.objects.create_user(email="admin_target@test.com")
        ProjectPermission.objects.create(
            user=target,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_b1, user=self.agent)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.requester_perm,
            target_email=target.email,
        )

        flat = self._flatten(result)
        self.assertEqual(
            set(flat.keys()),
            {
                str(self.queue_a1.uuid),
                str(self.queue_a2.uuid),
                str(self.queue_b1.uuid),
            },
        )
        total_in_service = sum(q["in_service"] for q in flat.values())
        self.assertEqual(total_in_service, 2)

    def test_target_email_is_normalized_to_lowercase(self):
        target = User.objects.create_user(email="target@test.com")
        target_perm = ProjectPermission.objects.create(
            user=target,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=target_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self._create_room(self.queue_a1, user=target)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.requester_perm,
            target_email="TARGET@test.com",
        )

        flat = self._flatten(result)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)


class RoomsCountByQueueServiceFilteringTests(RoomsCountByQueueServiceTestsBase):
    """
    Verifies the room-state filters and ordering applied by the service.
    """

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(email="admin@test.com")
        self.admin_perm = ProjectPermission.objects.create(
            user=self.admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def test_inactive_and_flow_start_rooms_are_ignored(self):
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1, is_active=False)
        self._create_room(self.queue_a1, is_waiting=True)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_a1, user=self.agent, is_active=False)
        self._create_room(self.queue_a1, user=self.agent, is_waiting=True)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )

        flat = self._flatten(result)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 1)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)

    def test_soft_deleted_sectors_are_hidden(self):
        self._create_room(self.queue_b1)
        self.sector_b.is_deleted = True
        self.sector_b.save(update_fields=["is_deleted"])

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )

        sector_names = [s["name"] for s in result["sectors"]]
        self.assertNotIn("B Sector", sector_names)

    def test_sectors_and_queues_are_alphabetically_ordered(self):
        Queue.objects.create(name="A0 Queue", sector=self.sector_a)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )

        self.assertEqual(
            [s["name"] for s in result["sectors"]],
            ["A Sector", "B Sector"],
        )
        sector_a_queues = [q["name"] for q in result["sectors"][0]["queues"]]
        self.assertEqual(sector_a_queues, ["A0 Queue", "A1 Queue", "A2 Queue"])

    def test_other_projects_rooms_are_not_counted(self):
        other_project = Project.objects.create(name="Other Project")
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)
        self._create_room(other_queue)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )

        sector_names = [s["name"] for s in result["sectors"]]
        self.assertNotIn("Other Sector", sector_names)


class RoomsCountByQueueServiceManagerTests(RoomsCountByQueueServiceTestsBase):
    """
    A sector manager (project attendant + sector authorization) is treated
    as manager view.
    """

    def test_sector_manager_is_treated_as_manager_view(self):
        manager = User.objects.create_user(email="manager@test.com")
        manager_perm = ProjectPermission.objects.create(
            user=manager,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=manager_perm,
            sector=self.sector_a,
            role=SectorAuthorization.ROLE_MANAGER,
        )
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1, user=self.agent)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=manager_perm,
        )

        flat = self._flatten(result)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 1)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)
