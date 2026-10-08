from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.rooms.services.rooms_count_by_agent_service import (
    RoomsCountByAgentService,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization

User = get_user_model()


class RoomsCountByAgentServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.other_sector = Sector.objects.create(
            name="Sales",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Support Queue", sector=self.sector)
        self.other_queue = Queue.objects.create(
            name="Sales Queue", sector=self.other_sector
        )
        self.admin = User.objects.create_user(
            email="admin@test.com", first_name="Admin"
        )
        self.admin_perm = ProjectPermission.objects.create(
            user=self.admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.service = RoomsCountByAgentService()

    def _agent(self, email, first_name, queue):
        user = User.objects.create_user(email=email, first_name=first_name)
        permission = ProjectPermission.objects.create(
            user=user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=permission,
            queue=queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        return user

    def _create_room(self, queue, *, user=None, is_active=True, is_waiting=False):
        return Room.objects.create(
            queue=queue,
            contact=Contact.objects.create(),
            user=user,
            is_active=is_active,
            is_waiting=is_waiting,
        )

    def test_orders_by_in_progress_then_name_and_uses_email_as_uuid(self):
        ana = self._agent("ana@test.com", "Ana", self.queue)
        bruno = self._agent("bruno@test.com", "Bruno", self.queue)
        carla = self._agent("carla@test.com", "Carla", self.queue)
        self._create_room(self.queue, user=ana)
        self._create_room(self.queue, user=bruno)
        self._create_room(self.queue, user=bruno)
        self._create_room(self.queue, user=carla)
        self._create_room(self.queue, user=carla)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )
        attendants = [agent for agent in result["agents"] if agent["name"] != "Admin"]

        self.assertEqual(
            [(agent["name"], agent["rooms_in_progress"]) for agent in attendants],
            [("Bruno", 2), ("Carla", 2), ("Ana", 1)],
        )
        self.assertEqual(attendants[0]["uuid"], "bruno@test.com")

    def test_awaiting_counts_unassigned_rooms_in_the_agent_queue(self):
        ana = self._agent("ana@test.com", "Ana", self.queue)
        self._create_room(self.queue)
        self._create_room(self.queue, is_active=False)
        self._create_room(self.queue, is_waiting=True)
        self._create_room(self.queue, user=ana)
        self._create_room(self.other_queue)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )
        ana_row = next(agent for agent in result["agents"] if agent["name"] == "Ana")
        self.assertEqual(ana_row["rooms_in_awaiting"], 1)
        self.assertEqual(ana_row["rooms_in_progress"], 1)

    def test_attendant_sees_only_themselves(self):
        ana = self._agent("ana@test.com", "Ana", self.queue)
        self._agent("bruno@test.com", "Bruno", self.queue)
        ana_perm = ProjectPermission.objects.get(user=ana, project=self.project)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=ana_perm,
        )

        self.assertEqual([agent["name"] for agent in result["agents"]], ["Ana"])

    def test_sector_manager_does_not_see_agents_from_other_sectors(self):
        self._agent("ana@test.com", "Ana", self.queue)
        self._agent("bruno@test.com", "Bruno", self.other_queue)
        manager = User.objects.create_user(email="manager@test.com", first_name="Mia")
        manager_perm = ProjectPermission.objects.create(
            user=manager,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=manager_perm,
            sector=self.sector,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=manager_perm,
        )

        self.assertEqual(
            sorted(agent["name"] for agent in result["agents"]),
            ["Ana", "Mia"],
        )
