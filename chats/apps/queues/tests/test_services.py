from datetime import time
from unittest.mock import patch
from django.test import TestCase

from chats.apps.projects.models.models import (
    Project,
    ProjectPermission,
    RoomRoutingType,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.services import QueueRouterService
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.accounts.models import User


class QueueRouterServiceTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.service = QueueRouterService(self.queue)

        self.agent_1 = User.objects.create(
            email="test_agent_1@example.com",
        )
        self.agent_2 = User.objects.create(
            email="test_agent_2@example.com",
        )

        for agent in [self.agent_1, self.agent_2]:
            perm = ProjectPermission.objects.create(
                project=self.project,
                user=agent,
                role=ProjectPermission.ROLE_ATTENDANT,
                status="ONLINE",
            )
            QueueAuthorization.objects.create(
                queue=self.queue,
                permission=perm,
                role=QueueAuthorization.ROLE_AGENT,
            )

    @patch("chats.apps.queues.services.logger")
    def test_route_rooms_when_queue_is_empty(self, mock_logger):
        self.service.route_rooms()

        mock_logger.info.assert_any_call(
            "No rooms to route for queue %s, ending routing", self.queue.uuid
        )

    @patch("chats.apps.queues.services.logger")
    def test_route_rooms_when_agents_are_offline(self, mock_logger):
        self.agent_1.project_permissions.update(status="OFFLINE")
        self.agent_2.project_permissions.update(status="OFFLINE")

        self.assertEqual(self.queue.online_agents.count(), 0)
        self.assertEqual(self.queue.available_agents.count(), 0)

        Room.objects.create(
            queue=self.queue,
            user=None,
        )

        self.service.route_rooms()

        mock_logger.info.assert_any_call(
            "No available agents for queue %s, ending routing", self.queue.uuid
        )

    @patch("chats.apps.queues.services.logger")
    def test_route_rooms_when_agents_are_online_but_not_available(self, mock_logger):
        self.assertEqual(self.queue.online_agents.count(), 2)
        self.assertEqual(self.queue.available_agents.count(), 2)

        Room.objects.create(
            queue=self.queue,
            user=self.agent_1,
        )
        Room.objects.create(
            queue=self.queue,
            user=self.agent_2,
        )

        self.assertEqual(self.queue.available_agents.count(), 0)

        Room.objects.create(
            queue=self.queue,
            user=None,
        )

        self.service.route_rooms()

        mock_logger.info.assert_any_call(
            "No available agents for queue %s, ending routing", self.queue.uuid
        )

    @patch("chats.apps.queues.services.logger")
    def test_route_rooms_when_agents_are_online_and_available(self, mock_logger):
        self.assertEqual(self.queue.online_agents.count(), 2)
        self.assertEqual(self.queue.available_agents.count(), 2)

        Room.objects.create(
            queue=self.queue,
            user=self.agent_1,
        )

        # Agent 1 is online but not available anymore,
        # because there is a room already assigned to this agent
        # and the rooms limit is 1
        self.assertEqual(self.queue.available_agents.count(), 1)

        room = Room.objects.create(
            queue=self.queue,
            user=None,
        )

        self.service.route_rooms()

        mock_logger.info.assert_any_call(
            "%s rooms routed for queue %s, ending routing", 1, self.queue.uuid
        )

        self.assertEqual(self.queue.available_agents.count(), 0)

        room.refresh_from_db()

        self.assertEqual(room.user, self.agent_2)
