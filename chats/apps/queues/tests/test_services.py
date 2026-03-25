import json
from datetime import time
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.accounts.models import User
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
                last_seen=timezone.now(),
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
        time_3_days_ago = now - timedelta(days=3)

        with patch("django.utils.timezone.now", return_value=time_1_day_ago):
            room_1 = Room.objects.create(queue=self.queue, user=None)

        with patch("django.utils.timezone.now", return_value=time_2_days_ago):
            room_2 = Room.objects.create(queue=self.queue, user=None)

        with patch("django.utils.timezone.now", return_value=time_3_days_ago):
            room_3 = Room.objects.create(queue=self.queue, user=self.agent_1)

        self.assertEqual(room_1.added_to_queue_at, time_1_day_ago)
        self.assertEqual(room_2.added_to_queue_at, time_2_days_ago)

        rooms = list(self.service.get_rooms_to_route())

        # room 3 is ignored because it has a user assigned
        self.assertNotIn(room_3, rooms)
        self.assertEqual(rooms, [room_2, room_1])

        added_to_queue_at = room_2.added_to_queue_at

        room_2.user = self.agent_1
        room_2.save()

        room_2.refresh_from_db()

        # This should not change because the room was already assigned to an agent
        self.assertEqual(room_2.added_to_queue_at, added_to_queue_at)

        rooms = list(self.service.get_rooms_to_route())

        self.assertEqual(rooms, [room_1])

        room_2.user = None
        room_2.save()

        room_2.refresh_from_db()

        # This should change because the room was not assigned to an user
        self.assertNotEqual(room_2.added_to_queue_at, added_to_queue_at)
        self.assertGreater(room_2.added_to_queue_at, room_1.added_to_queue_at)

        rooms = list(self.service.get_rooms_to_route())

        # The order now is reversed because the room_2 has been added to the queue
        # after the room_1 (after removing the assigned user)
        # which is the equivalent of sending the room back to the queue
        self.assertEqual(rooms, [room_1, room_2])

        room_1.user = self.agent_2
        room_1.save()


class RaceConditionTestCase(TestCase):
    """
    Tests for race condition protection in route_rooms.

    These tests validate that when an agent goes OFFLINE between
    get_available_agent() and room.save(), the room is NOT assigned
    to the offline agent.
    """

    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project Race Condition",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )

        self.agent = User.objects.create(
            email="agent_race@example.com",
            first_name="Agent",
            last_name="Race",
        )
        self.agent_permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
            last_seen=timezone.now(),
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.agent_permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

    @patch("chats.apps.queues.services.logger")
    def test_room_not_assigned_when_agent_goes_offline_during_routing(
        self, mock_logger
    ):
        """
        Test that simulates race condition:
        1. Agent is ONLINE when get_available_agent() is called
        2. Agent goes OFFLINE before room.save()
        3. Room should NOT be assigned to the offline agent

        This test validates the fix works correctly.
        """
        # Create a room to be routed
        room = Room.objects.create(queue=self.queue, user=None)

        service = QueueRouterService(self.queue)

        # Store original get_available_agent
        original_get_available_agent = self.queue.get_available_agent

        def get_available_agent_and_go_offline():
            """
            Simulates race condition:
            Returns the agent, then immediately sets them OFFLINE
            """
            agent = original_get_available_agent()
            if agent:
                # Simulate agent going offline RIGHT AFTER being selected
                ProjectPermission.objects.filter(
                    user=agent, project=self.project
                ).update(status="OFFLINE")
            return agent

        # Patch get_available_agent to simulate race condition
        with patch.object(
            self.queue,
            "get_available_agent",
            side_effect=get_available_agent_and_go_offline,
        ):
            service.route_rooms()

        # Verify the room was NOT assigned to the offline agent
        room.refresh_from_db()
        self.assertIsNone(room.user)

        # Verify the log message was generated
        mock_logger.info.assert_any_call(
            "Agent %s is no longer online for room %s, skipping",
            self.agent.email,
            room.uuid,
        )

    @patch("chats.apps.queues.services.logger")
    def test_room_assigned_when_agent_stays_online(self, mock_logger):
        """
        Test that when agent stays ONLINE, room is assigned normally.
        This is the happy path - no race condition.
        """
        # Create a room to be routed
        room = Room.objects.create(queue=self.queue, user=None)

        service = QueueRouterService(self.queue)
        service.route_rooms()

        # Verify the room WAS assigned to the online agent
        room.refresh_from_db()
        self.assertEqual(room.user, self.agent)

        # Verify success log
        mock_logger.info.assert_any_call(
            "%s rooms routed for queue %s, ending routing", 1, self.queue.uuid
        )

    @patch("chats.apps.queues.services.logger")
    def test_room_stays_unassigned_when_only_agent_goes_offline(self, mock_logger):
        """
        Test that when the only available agent goes offline during routing,
        the room stays unassigned (not assigned to offline agent).

        Note: Current implementation moves to next ROOM, not next agent.
        This test validates that at least the offline agent doesn't get the room.
        """
        # Create a room to be routed
        room = Room.objects.create(queue=self.queue, user=None)

        service = QueueRouterService(self.queue)

        original_get_available_agent = self.queue.get_available_agent

        def get_available_agent_then_go_offline():
            """Returns the agent, then sets them offline"""
            agent = original_get_available_agent()
            if agent:
                ProjectPermission.objects.filter(
                    user=agent, project=self.project
                ).update(status="OFFLINE")
            return agent

        with patch.object(
            self.queue,
            "get_available_agent",
            side_effect=get_available_agent_then_go_offline,
        ):
            service.route_rooms()

        # Verify the room was NOT assigned to the offline agent
        room.refresh_from_db()
        self.assertIsNone(room.user)

        # Verify log shows agent was skipped
        mock_logger.info.assert_any_call(
            "Agent %s is no longer online for room %s, skipping",
            self.agent.email,
            room.uuid,
        )
