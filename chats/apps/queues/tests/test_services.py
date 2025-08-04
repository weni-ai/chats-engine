from datetime import time
import json
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.projects.models.models import (
    Project,
    ProjectPermission,
    RoomRoutingType,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.services import QueueRouterService
from chats.apps.rooms.choices import RoomFeedbackMethods
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
            email="mirosmar@example.com",
            first_name="Mirosmar",
            last_name="José de Camargo",
        )
        self.agent_2 = User.objects.create(
            email="welson@example.com",
            first_name="Welson",
            last_name="David de Camargo",
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

    def test_cannot_initialize_service_when_the_project_routing_type_is_not_queue_priority(
        self,
    ):
        self.project.room_routing_type = RoomRoutingType.GENERAL
        self.project.save()

        with self.assertRaises(ValueError) as context:
            QueueRouterService(self.queue)

        self.assertEqual(
            str(context.exception),
            "Queue priority routing is not enabled for this project",
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

        self.assertEqual(room.messages.count(), 1)

        try:
            message_text = json.loads(room.messages.first().text)
        except json.JSONDecodeError:
            self.fail("Message text is not a valid JSON")

        self.assertEqual(message_text.get("method"), RoomFeedbackMethods.ROOM_TRANSFER)
        self.assertEqual(
            message_text.get("content", {}).get("action"), "auto_assign_from_queue"
        )
        self.assertEqual(
            message_text.get("content", {}).get("from"),
            {"type": "queue", "name": self.queue.name, "uuid": str(self.queue.uuid)},
        )
        self.assertEqual(
            message_text.get("content", {}).get("to"),
            {
                "type": "user",
                "name": self.agent_2.name,
                "email": self.agent_2.email,
                "id": str(self.agent_2.id),
            },
        )

    def test_get_rooms_to_route_order(self):
        self.assertEqual(self.service.get_rooms_to_route().count(), 0)

        now = timezone.now()
        time_1_day_ago = now - timedelta(days=1)
        time_2_days_ago = now - timedelta(days=2)

        with patch("django.utils.timezone.now", return_value=time_1_day_ago):
            room_1 = Room.objects.create(queue=self.queue, user=None)

        with patch("django.utils.timezone.now", return_value=time_2_days_ago):
            room_2 = Room.objects.create(queue=self.queue, user=None)

        self.assertEqual(list(self.service.get_rooms_to_route()), [room_2, room_1])
