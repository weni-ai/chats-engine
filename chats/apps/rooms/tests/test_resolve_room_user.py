from datetime import time
from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import (
    FlowStart,
    LinkContact,
    Project,
    ProjectPermission,
    RoomRoutingType,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.rooms.usecases.resolve_room_user import ResolveRoomUserUseCase
from chats.apps.sectors.models import Sector

GROWTHBOOK_PATCH = (
    "chats.apps.queues.models.is_feature_active_for_attributes"
)


class ResolveRoomUserFlowStartTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-1", name="Test Contact"
        )

        self.agent = User.objects.create(email="agent@example.com")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )

        self.flow_start = FlowStart.objects.create(
            project=self.project,
            permission=self.permission,
            flow="test-flow",
        )

        self.usecase = ResolveRoomUserUseCase(self.queue, self.project)

    def test_returns_flow_start_user_when_contact_is_created_and_permission_online(
        self,
    ):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
            last_flow_start=self.flow_start,
        )

        self.assertEqual(result, self.agent)

    def test_returns_flow_start_user_when_no_rooms_after_flow_start_and_permission_online(
        self,
    ):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=False,
            last_flow_start=self.flow_start,
        )

        self.assertEqual(result, self.agent)

    def test_skips_flow_start_when_permission_offline(self):
        self.permission.status = "OFFLINE"
        self.permission.save(update_fields=["status"])

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
            last_flow_start=self.flow_start,
        )

        self.assertIsNone(result)

    def test_skips_flow_start_when_rooms_exist_after_flow_start(self):
        Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=False,
            last_flow_start=self.flow_start,
        )

        self.assertIsNone(result)

    def test_skips_flow_start_when_none(self):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
            last_flow_start=None,
        )

        self.assertIsNone(result)


class ResolveRoomUserLinkedUserTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-linked", name="Linked Contact"
        )

        self.linked_agent = User.objects.create(email="linked@example.com")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.linked_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )
        LinkContact.objects.create(
            user=self.linked_agent,
            contact=self.contact,
            project=self.project,
        )

        self.usecase = ResolveRoomUserUseCase(self.queue, self.project)

    def test_returns_linked_user_when_not_created_and_linked_user_online(self):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=False,
        )

        self.assertEqual(result, self.linked_agent)

    def test_skips_linked_user_when_is_created(self):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertIsNone(result)

    def test_skips_linked_user_when_linked_user_offline(self):
        self.permission.status = "OFFLINE"
        self.permission.save(update_fields=["status"])

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=False,
        )

        self.assertIsNone(result)


class ResolveRoomUserExplicitUserTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-explicit", name="Explicit Contact"
        )

        self.agent = User.objects.create(email="explicit@example.com")

        self.usecase = ResolveRoomUserUseCase(self.queue, self.project)

    def test_returns_explicit_user_when_online_in_project(self):
        ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )

        result = self.usecase.execute(
            contact=self.contact,
            user=self.agent,
            is_created=True,
        )

        self.assertEqual(result, self.agent)

    def test_skips_explicit_user_when_not_online(self):
        ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="OFFLINE",
        )

        result = self.usecase.execute(
            contact=self.contact,
            user=self.agent,
            is_created=True,
        )

        self.assertIsNone(result)

    def test_skips_explicit_user_when_none(self):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertIsNone(result)


@patch(GROWTHBOOK_PATCH, return_value=False)
class ResolveRoomUserQueuePriorityTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-qp", name="QP Contact"
        )

        self.agent = User.objects.create(email="qp-agent@example.com")
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

        self.usecase = ResolveRoomUserUseCase(self.queue, self.project)

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=False,
    )
    @patch("chats.apps.rooms.usecases.resolve_room_user.start_queue_priority_routing")
    def test_queue_priority_empty_queue_returns_available_agent(
        self, mock_routing, mock_flag, _mock_gb
    ):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertEqual(result, self.agent)
        mock_routing.assert_not_called()

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=False,
    )
    @patch("chats.apps.rooms.usecases.resolve_room_user.start_queue_priority_routing")
    def test_queue_priority_empty_queue_no_agent_returns_none(
        self, mock_routing, mock_flag, _mock_gb
    ):
        self.agent.delete()

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertIsNone(result)
        mock_routing.assert_not_called()

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=True,
    )
    @patch("chats.apps.rooms.usecases.resolve_room_user.start_queue_priority_routing")
    def test_queue_priority_empty_queue_agent_fails_capacity_recheck(
        self, mock_routing, mock_flag, _mock_gb
    ):
        for i in range(5):
            Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(external_id=f"overloaded-{i}"),
                user=self.agent,
                is_active=True,
            )

        with patch.object(Queue, "get_available_agent", return_value=self.agent):
            result = self.usecase.execute(
                contact=self.contact,
                user=None,
                is_created=True,
            )

        self.assertIsNone(result)
        mock_routing.assert_called_once_with(self.queue)

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=False,
    )
    @patch("chats.apps.rooms.usecases.resolve_room_user.start_queue_priority_routing")
    def test_queue_priority_empty_queue_capacity_recheck_flag_off(
        self, mock_routing, mock_flag, _mock_gb
    ):
        for i in range(5):
            Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(external_id=f"overloaded-{i}"),
                user=self.agent,
                is_active=True,
            )

        with patch.object(Queue, "get_available_agent", return_value=self.agent):
            result = self.usecase.execute(
                contact=self.contact,
                user=None,
                is_created=True,
            )

        self.assertEqual(result, self.agent)
        mock_routing.assert_not_called()

    @patch("chats.apps.rooms.usecases.resolve_room_user.start_queue_priority_routing")
    def test_queue_priority_non_empty_queue_returns_none(
        self, mock_routing, _mock_gb
    ):
        Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(external_id="waiting-contact"),
            user=None,
            is_active=True,
        )

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertIsNone(result)
        mock_routing.assert_called_once_with(self.queue)


@patch(GROWTHBOOK_PATCH, return_value=False)
class ResolveRoomUserGeneralRoutingTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.GENERAL,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-general", name="General Contact"
        )

        self.agent = User.objects.create(email="general-agent@example.com")
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

        self.usecase = ResolveRoomUserUseCase(self.queue, self.project)

    def test_general_routing_with_waiting_rooms_returns_none(self, _mock_gb):
        Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(external_id="waiting-general"),
            user=None,
            is_active=True,
        )

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertIsNone(result)

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=False,
    )
    def test_general_routing_returns_available_agent(self, mock_flag, _mock_gb):
        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertEqual(result, self.agent)

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=False,
    )
    def test_general_routing_no_agent_returns_none(self, mock_flag, _mock_gb):
        self.agent.delete()

        result = self.usecase.execute(
            contact=self.contact,
            user=None,
            is_created=True,
        )

        self.assertIsNone(result)

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=True,
    )
    def test_general_routing_agent_fails_capacity_recheck(self, mock_flag, _mock_gb):
        for i in range(5):
            Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(external_id=f"general-overloaded-{i}"),
                user=self.agent,
                is_active=True,
            )

        with patch.object(Queue, "get_available_agent", return_value=self.agent):
            result = self.usecase.execute(
                contact=self.contact,
                user=None,
                is_created=True,
            )

        self.assertIsNone(result)

    @patch(
        "chats.apps.rooms.usecases.resolve_room_user.is_feature_active",
        return_value=False,
    )
    def test_general_routing_capacity_recheck_flag_off(self, mock_flag, _mock_gb):
        for i in range(5):
            Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(external_id=f"general-overloaded-{i}"),
                user=self.agent,
                is_active=True,
            )

        with patch.object(Queue, "get_available_agent", return_value=self.agent):
            result = self.usecase.execute(
                contact=self.contact,
                user=None,
                is_created=True,
            )

        self.assertEqual(result, self.agent)
