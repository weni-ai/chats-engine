from datetime import time

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import (
    Project,
    ProjectPermission,
    RoomRoutingType,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.usecases.can_agent_receive_room import (
    AgentCapacityResult,
    CanAgentReceiveRoomUseCase,
)
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import GroupSector, Sector, SectorGroupSector


class CanAgentReceiveRoomUseCaseTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=3,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=3,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.other_queue = Queue.objects.create(
            name="Other Queue", sector=self.other_sector
        )

        self.agent = User.objects.create(email="agent@example.com")
        permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.usecase = CanAgentReceiveRoomUseCase(self.queue)

    def test_returns_true_when_agent_has_no_active_rooms(self):
        result = self.usecase.execute(self.agent)

        self.assertIsInstance(result, AgentCapacityResult)
        self.assertTrue(result.can_receive)
        self.assertEqual(result.active_rooms_count, 0)
        self.assertEqual(result.limit, 3)
        self.assertIsNone(result.reason)

    def test_returns_true_when_agent_is_below_limit(self):
        Room.objects.create(queue=self.queue, user=self.agent, is_active=True)
        Room.objects.create(queue=self.queue, user=self.agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertTrue(result.can_receive)
        self.assertEqual(result.active_rooms_count, 2)
        self.assertEqual(result.limit, 3)

    def test_returns_false_when_agent_reached_limit(self):
        for _ in range(3):
            Room.objects.create(queue=self.queue, user=self.agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 3)
        self.assertEqual(result.limit, 3)
        self.assertIsNotNone(result.reason)

    def test_returns_false_when_agent_exceeded_limit(self):
        """
        Scenario that motivated this usecase: somehow the agent
        ended up with more rooms than the limit (race condition).
        """
        for _ in range(5):
            Room.objects.create(queue=self.queue, user=self.agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 5)
        self.assertEqual(result.limit, 3)

    def test_closed_rooms_do_not_count(self):
        for _ in range(3):
            Room.objects.create(queue=self.queue, user=self.agent, is_active=False)

        result = self.usecase.execute(self.agent)

        self.assertTrue(result.can_receive)
        self.assertEqual(result.active_rooms_count, 0)

    def test_rooms_from_other_sectors_do_not_count(self):
        for _ in range(3):
            Room.objects.create(queue=self.other_queue, user=self.agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertTrue(result.can_receive)
        self.assertEqual(result.active_rooms_count, 0)

    def test_rooms_from_sibling_queues_in_same_sector_do_count(self):
        sibling_queue = Queue.objects.create(name="Sibling Queue", sector=self.sector)
        for _ in range(3):
            Room.objects.create(queue=sibling_queue, user=self.agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 3)

    def test_group_sector_limit_overrides_sector_limit(self):
        group_sector = GroupSector.objects.create(
            name="Group", project=self.project, rooms_limit=1
        )
        SectorGroupSector.objects.create(sector_group=group_sector, sector=self.sector)
        Room.objects.create(queue=self.queue, user=self.agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 1)
        self.assertEqual(result.limit, 1)

    def test_rooms_assigned_to_other_agents_do_not_count(self):
        other_agent = User.objects.create(email="other@example.com")
        for _ in range(3):
            Room.objects.create(queue=self.queue, user=other_agent, is_active=True)

        result = self.usecase.execute(self.agent)

        self.assertTrue(result.can_receive)
        self.assertEqual(result.active_rooms_count, 0)


class CanAgentReceiveRoomUseCaseCustomLimitTestCase(TestCase):
    """
    End-to-end verification that CanAgentReceiveRoomUseCase respects the
    per-agent custom_rooms_limit on ProjectPermission, in sync with
    Queue.available_agents.
    """

    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=2,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.agent = User.objects.create(email="agent@example.com")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.usecase = CanAgentReceiveRoomUseCase(self.queue)

    def _create_active_rooms(self, count):
        for _ in range(count):
            Room.objects.create(queue=self.queue, user=self.agent, is_active=True)

    def _activate_custom_limit(self, total):
        self.permission.is_custom_limit_active = True
        self.permission.custom_rooms_limit = total
        self.permission.save(
            update_fields=["is_custom_limit_active", "custom_rooms_limit"]
        )

    def test_falls_back_to_sector_limit_when_custom_limit_inactive(self):
        """When is_custom_limit_active=False, sector.rooms_limit is used."""
        self._create_active_rooms(2)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 2)
        self.assertEqual(result.limit, 2)

    def test_custom_limit_allows_agent_beyond_sector_limit(self):
        """Active custom_rooms_limit > sector.rooms_limit lifts the cap."""
        self._activate_custom_limit(total=5)
        self._create_active_rooms(3)

        result = self.usecase.execute(self.agent)

        self.assertTrue(result.can_receive)
        self.assertEqual(result.active_rooms_count, 3)
        self.assertEqual(result.limit, 5)

    def test_available_agents_and_execute_agree_on_block_at_custom_limit(self):
        """When the agent reaches custom_rooms_limit, both layers block."""
        self._activate_custom_limit(total=3)
        self._create_active_rooms(3)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 3)
        self.assertEqual(result.limit, 3)
        self.assertNotIn(self.agent, self.queue.available_agents)

    def test_deactivating_custom_limit_falls_back_to_sector_limit(self):
        """Switching is_custom_limit_active to False restores the sector limit."""
        self._activate_custom_limit(total=5)
        self._create_active_rooms(3)

        result = self.usecase.execute(self.agent)
        self.assertTrue(result.can_receive)
        self.assertEqual(result.limit, 5)

        self.permission.is_custom_limit_active = False
        self.permission.save(update_fields=["is_custom_limit_active"])

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.active_rooms_count, 3)
        self.assertEqual(result.limit, 2)

    def test_inactive_custom_limit_field_is_ignored_even_when_set(self):
        """custom_rooms_limit alone (without is_custom_limit_active=True) is ignored."""
        self.permission.is_custom_limit_active = False
        self.permission.custom_rooms_limit = 10
        self.permission.save(
            update_fields=["is_custom_limit_active", "custom_rooms_limit"]
        )
        self._create_active_rooms(2)

        result = self.usecase.execute(self.agent)

        self.assertFalse(result.can_receive)
        self.assertEqual(result.limit, 2)
