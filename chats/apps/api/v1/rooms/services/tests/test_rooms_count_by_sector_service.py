from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.rooms.services.rooms_count_by_sector_service import (
    RoomsCountBySectorService,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization

User = get_user_model()


class RoomsCountBySectorServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector_apple = Sector.objects.create(
            name="Apple",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_banana = Sector.objects.create(
            name="Banana",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_mango = Sector.objects.create(
            name="Mango",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue_apple = Queue.objects.create(
            name="Apple Queue", sector=self.sector_apple
        )
        self.queue_banana = Queue.objects.create(
            name="Banana Queue", sector=self.sector_banana
        )
        self.queue_mango = Queue.objects.create(
            name="Mango Queue", sector=self.sector_mango
        )
        self.agent = User.objects.create_user(
            email="agent@test.com", first_name="Agent"
        )
        self.admin = User.objects.create_user(email="admin@test.com")
        self.admin_perm = ProjectPermission.objects.create(
            user=self.admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.service = RoomsCountBySectorService()

    def _create_room(self, queue, *, user=None, is_active=True, is_waiting=False):
        return Room.objects.create(
            queue=queue,
            contact=Contact.objects.create(),
            user=user,
            is_active=is_active,
            is_waiting=is_waiting,
        )

    def test_orders_by_in_progress_then_name(self):
        self._create_room(self.queue_apple, user=self.agent)
        self._create_room(self.queue_apple, user=self.agent)
        self._create_room(self.queue_banana, user=self.agent)
        self._create_room(self.queue_banana, user=self.agent)
        self._create_room(self.queue_mango, user=self.agent)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )

        self.assertEqual(
            [sector["name"] for sector in result["sectors"]],
            ["Apple", "Banana", "Mango"],
        )
        by_name = {sector["name"]: sector for sector in result["sectors"]}
        self.assertEqual(by_name["Apple"]["rooms_in_progress"], 2)
        self.assertEqual(by_name["Banana"]["rooms_in_progress"], 2)
        self.assertEqual(by_name["Mango"]["rooms_in_progress"], 1)
        self.assertEqual(by_name["Apple"]["uuid"], str(self.sector_apple.uuid))

    def test_counts_awaiting_and_ignores_closed_and_flow_start(self):
        self._create_room(self.queue_apple)
        self._create_room(self.queue_apple, is_active=False)
        self._create_room(self.queue_apple, is_waiting=True)
        self._create_room(self.queue_apple, user=self.agent)
        self._create_room(self.queue_apple, user=self.agent, is_active=False)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=self.admin_perm,
        )
        apple = next(
            sector for sector in result["sectors"] if sector["name"] == "Apple"
        )
        self.assertEqual(apple["rooms_in_awaiting"], 1)
        self.assertEqual(apple["rooms_in_progress"], 1)

    def test_sector_manager_sees_only_managed_sectors_with_global_in_progress(self):
        manager = User.objects.create_user(email="manager@test.com")
        manager_perm = ProjectPermission.objects.create(
            user=manager,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=manager_perm,
            sector=self.sector_apple,
            role=SectorAuthorization.ROLE_MANAGER,
        )
        self._create_room(self.queue_apple)
        self._create_room(self.queue_apple, user=self.agent)
        self._create_room(self.queue_banana, user=self.agent)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=manager_perm,
        )

        self.assertEqual([sector["name"] for sector in result["sectors"]], ["Apple"])
        self.assertEqual(result["sectors"][0]["rooms_in_awaiting"], 1)
        self.assertEqual(result["sectors"][0]["rooms_in_progress"], 1)

    def test_attendant_counts_only_own_in_progress_rooms(self):
        attendant = User.objects.create_user(email="attendant@test.com")
        attendant_perm = ProjectPermission.objects.create(
            user=attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=attendant_perm,
            queue=self.queue_apple,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self._create_room(self.queue_apple, user=attendant)
        self._create_room(self.queue_apple, user=self.agent)
        self._create_room(self.queue_apple)

        result = self.service.get_counts(
            project_uuid=self.project.uuid,
            requesting_permission=attendant_perm,
        )

        self.assertEqual([sector["name"] for sector in result["sectors"]], ["Apple"])
        self.assertEqual(result["sectors"][0]["rooms_in_awaiting"], 1)
        self.assertEqual(result["sectors"][0]["rooms_in_progress"], 1)
