from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus, CustomStatusType
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import GroupSector, Sector

User = get_user_model()


def create_user(nickname: str = "fake"):
    return User.objects.create_user("{}@user.com".format(nickname), nickname)


class ConstraintTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project_permission = ProjectPermission.objects.get(
            uuid="e416fd45-2896-43a5-bd7a-5067f03c77fa"
        )
        self.queue = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")
        self.queue_auth = QueueAuthorization.objects.get(
            uuid="3717f056-7ea5-4d38-80f5-ba907132807c"
        )

    def test_unique_queue_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            Queue.objects.create(name=self.queue.name, sector=self.queue.sector)
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_queue_name"'
            in str(context.exception)
        )

    def test_unique_queue_auth_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            QueueAuthorization.objects.create(
                queue=self.queue_auth.queue, permission=self.queue_auth.permission
            )
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_queue_auth"'
            in str(context.exception)
        )


class QueueSetUpMixin(TestCase):
    def setUp(self):
        super().setUp()

        self.project = Project.objects.create(name="Test chat Project 1")
        self.sector = Sector.objects.create(
            name="Test chat Sector 1",
            project=self.project,
            rooms_limit=1,
            work_start="08:00:00",
            work_end="17:00:00",
        )

        self.manager = create_user("manager")
        self.manager_2 = create_user("manager2")
        self.manager_3 = create_user("manager3")

        self.agent = create_user("agent")
        self.agent_2 = create_user("agent2")

        self.agent_permission = self.agent.project_permissions.create(
            project=self.project, role=ProjectPermission.ROLE_ATTENDANT
        )
        self.agent_2_permission = self.agent_2.project_permissions.create(
            project=self.project, role=ProjectPermission.ROLE_ATTENDANT
        )

        self.queue = Queue.objects.create(name="Q1", sector=self.sector)

        self.queue.authorizations.create(permission=self.agent_permission)
        self.queue.authorizations.create(permission=self.agent_2_permission)

        self.contact = Contact.objects.create(
            name="Contact test 123", email="test@user.com"
        )
        self.agent_auth = QueueAuthorization.objects.get(
            permission=self.agent_permission
        )
        self.room = Room.objects.create(
            contact=self.contact, is_active=True, queue=self.queue
        )


class QueueAvailableAgentsDefaultTestCase(QueueSetUpMixin, TestCase):
    def test_available_agents_returns_online_agents(self):
        self.agent_permission.status = "ONLINE"
        self.agent_permission.save()

        self.assertIn(self.agent, self.queue.available_agents)
        self.assertEqual(self.queue.available_agents.count(), 1)

    def test_when_exceeding_limit_of_active_rooms_the_agent_is_no_longer_returned(self):
        self.room.user = self.agent
        self.room.save()

        self.agent_permission.status = "ONLINE"
        self.agent_permission.save()

        self.assertNotIn(self.agent, self.queue.available_agents)
        self.assertEqual(self.queue.available_agents.count(), 0)

    def tests_if_disable_a_room_the_agent_is_still_returned(self):
        self.room.user = self.agent
        self.room.is_active = False
        self.room.save()

        self.agent_permission.status = "ONLINE"
        self.agent_permission.save()

        self.assertIn(self.agent, self.queue.available_agents)

    def test_if_2_online_agents_are_returned_in_available_agents(self):
        self.agent_permission.status = "ONLINE"
        self.agent_permission.save()
        self.agent_2_permission.status = "ONLINE"
        self.agent_2_permission.save()

        self.assertEqual(self.queue.available_agents.count(), 2)

    def test_if_available_agents_returns_0_agents_if_no_one_is_online(self):
        self.assertEqual(self.queue.available_agents.count(), 0)

    def tests_if_when_there_are_2_agents_it_returns_sorted_by_active_rooms_count(self):
        self.sector.rooms_limit = 5
        self.sector.save()

        self.room.user = self.agent
        self.room.save()

        self.agent_permission.status = "ONLINE"
        self.agent_permission.save()
        self.agent_2_permission.status = "ONLINE"
        self.agent_2_permission.save()

        self.assertEqual(self.agent_2, self.queue.available_agents.first())


class QueueAvailableAgentsGaneralTestCase(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.queue = Queue.objects.get(pk="f2519480-7e58-4fc4-9894-9ab1769e29cf")
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.project.config = {"routing_option": "general"}
        self.project.save()
        self.sector = self.queue.sector
        self.sector.rooms_limit = 4
        self.sector.save()

    def test_1_online_user_with_3_active_1_closed(self):
        user = User.objects.get(email="amywong@chats.weni.ai")
        Room.objects.update(user=user)
        Room.objects.first().close()
        self.project.permissions.filter(user=user).update(status="ONLINE")

        available_agents = self.queue.available_agents

        self.assertEqual(available_agents.count(), 1)

    def test_1_online_user_with_2_active_1_closed(self):
        user = User.objects.get(email="amywong@chats.weni.ai")
        user.rooms.first().close()
        self.project.permissions.filter(user=user).update(status="ONLINE")

        available_agents = self.queue.available_agents

        self.assertEqual(available_agents.count(), 1)
        self.assertEqual(available_agents.first().active_and_day_closed_rooms, 3)
        self.assertEqual(available_agents.first().active_rooms_count, 2)

    def test_2_online_users_with_2_active_1_closed_second_agent_empty(self):
        """
        Verify if the first in queue will be the agent with the least rooms
        """
        user = User.objects.get(email="amywong@chats.weni.ai")
        user.rooms.first().close()
        self.project.permissions.filter(user=user).update(status="ONLINE")
        self.project.permissions.filter(user__email="linalawson@chats.weni.ai").update(
            status="ONLINE"
        )

        available_agents = self.queue.available_agents

        self.assertEqual(available_agents.count(), 2)
        self.assertEqual(available_agents.first().active_rooms_count, 0)
        self.assertEqual(available_agents.first().email, "linalawson@chats.weni.ai")


class PropertyTests(QueueSetUpMixin, APITestCase):
    def test_name_property(self):
        """
        Verify if the property for get queue name its returning the correct value.
        """
        self.assertEqual(self.queue.__str__(), "Q1")

    def test_queue_object_property(self):
        """
        Verify if the property for get queue instance its returning the correct value.
        """
        self.assertEqual(self.queue.queue, self.queue)

    def test_limit_property(self):
        """
        Verify if the property for get limit for attending its returning the correct value.
        """
        self.assertEqual(self.queue.limit, 1)

    def test_get_permission_property(self):
        """
        Verify if the property for get permissions its returning the correct value.
        """
        permission_returned = self.queue.get_permission(self.agent)
        self.assertEqual(permission_returned, self.agent_permission)

    def test_get_agent_count_property(self):
        """
        Verify if the property for get agent count its returning the correct value.
        """
        self.assertEqual(self.queue.agent_count, 2)

    def test_get_agent_property(self):
        """
        Verify if the property for get agents its returning the correct value.
        """
        self.assertTrue(self.agent and self.agent_2 in self.queue.agents)

    def test_get_or_create_user_authorization_property(self):
        """
        Verify if the property for get or create user authorizations agents its working correctly.
        """
        get_or_create_property = self.queue.get_or_create_user_authorization(self.agent)
        self.assertTrue(self.agent, get_or_create_property)

    def test_set_queue_authorization_property(self):
        """
        Verify if the property for set authorization its working correctly.
        """
        get_or_create_property = self.queue.set_queue_authorization(self.agent, role=1)
        self.assertTrue(self.agent, get_or_create_property)

    def test_get_permission_queue_auth_property(self):
        """
        Verify if the property for get permission in queue auth its returning the correct value.
        """
        get_or_create_property = self.queue.set_queue_authorization(self.agent, role=1)
        self.assertTrue(
            get_or_create_property.get_permission(self.agent), self.agent_auth
        )

    def test_is_agent_property(self):
        """
        Verify if the property for get if user its agent its returning the correct value.
        """
        self.assertEqual(self.agent_auth.is_agent, True)

    def test_user_property(self):
        """
        Verify if the property for get user its returning the correct value.
        """
        self.assertEqual(self.agent_auth.user, self.agent)

    def test_can_list_property(self):
        """
        Verify if the property for get if user can list its returning the correct value.
        """
        self.assertEqual(self.agent_auth.can_list, True)


class TestQueueOnlineAgents(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test chat Project 1")
        self.sector = Sector.objects.create(
            name="Test chat Sector 1",
            project=self.project,
            rooms_limit=5,
            work_start="08:00:00",
            work_end="17:00:00",
        )
        self.queue = Queue.objects.create(name="Q1", sector=self.sector)

        self.agent_1 = create_user("agent1")
        self.agent_2 = create_user("agent2")
        self.agent_3 = create_user("agent3")

        for agent in [self.agent_1, self.agent_2, self.agent_3]:
            agent.project_permissions.create(
                project=self.project,
                role=ProjectPermission.ROLE_ATTENDANT,
                status="ONLINE",
            )
            self.queue.authorizations.create(
                permission=agent.project_permissions.first()
            )

        self.custom_status_type = CustomStatusType.objects.create(
            name="Test custom status type",
            project=self.project,
        )
        self.in_service_custom_status_type = CustomStatusType.objects.create(
            name="In-Service",
            project=self.project,
        )

    def test_online_agents_returns_only_online_agents(self):
        self.agent_1.project_permissions.update(status="OFFLINE")
        self.assertEqual(self.queue.online_agents.count(), 2)
        self.assertNotIn(self.agent_1, self.queue.online_agents)

    def test_online_agents_returns_agents_with_active_custom_status(self):
        custom_status = CustomStatus.objects.create(
            user=self.agent_1,
            status_type=self.custom_status_type,
            is_active=True,
        )
        self.assertEqual(self.queue.online_agents.count(), 2)
        self.assertNotIn(self.agent_1, self.queue.online_agents)

        custom_status.is_active = False
        custom_status.save(update_fields=["is_active"])
        self.assertEqual(self.queue.online_agents.count(), 3)
        self.assertIn(self.agent_1, self.queue.online_agents)

    def test_online_agents_returns_agents_with_in_service_custom_status(self):
        CustomStatus.objects.create(
            user=self.agent_1,
            status_type=self.in_service_custom_status_type,
            is_active=True,
        )
        self.assertEqual(self.queue.online_agents.count(), 3)
        self.assertIn(self.agent_1, self.queue.online_agents)

        custom_status = CustomStatus.objects.create(
            user=self.agent_1,
            status_type=self.custom_status_type,
            is_active=True,
        )
        self.assertEqual(self.queue.online_agents.count(), 2)
        self.assertNotIn(self.agent_1, self.queue.online_agents)

        custom_status.is_active = False
        custom_status.save(update_fields=["is_active"])
        self.assertEqual(self.queue.online_agents.count(), 3)
        self.assertIn(self.agent_1, self.queue.online_agents)


class TestQueueGetAvailableAgent(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test chat Project 1")
        self.sector = Sector.objects.create(
            name="Test chat Sector 1",
            project=self.project,
            rooms_limit=5,
            work_start="08:00:00",
            work_end="17:00:00",
        )
        self.queue = Queue.objects.create(name="Q1", sector=self.sector)

        self.agent_1 = create_user("agent1")
        self.agent_2 = create_user("agent2")
        self.agent_3 = create_user("agent3")

        for agent in [self.agent_1, self.agent_2, self.agent_3]:
            agent.project_permissions.create(
                project=self.project,
                role=ProjectPermission.ROLE_ATTENDANT,
                status="ONLINE",
            )
            self.queue.authorizations.create(
                permission=agent.project_permissions.first()
            )

    def test_get_available_agent_returns_agent_with_least_rooms(self):
        for i in range(3):
            # Agent 1 has 3 active rooms
            Room.objects.create(user=self.agent_1, queue=self.queue, is_active=True)

        for i in range(2):
            # Agent 2 has 2 active rooms
            Room.objects.create(user=self.agent_2, queue=self.queue, is_active=True)

        for i in range(1):
            # Agent 3 has 1 active room
            Room.objects.create(user=self.agent_3, queue=self.queue, is_active=True)

        available_agent = self.queue.get_available_agent()
        self.assertEqual(available_agent, self.agent_3)

    def test_get_available_agent_returns_random_agent_if_rooms_count_is_equal(self):
        for i in range(3):
            # Agent 1 has 3 active rooms
            Room.objects.create(user=self.agent_1, queue=self.queue, is_active=True)

        for i in range(2):
            # Agent 2 has 2 active rooms
            Room.objects.create(user=self.agent_2, queue=self.queue, is_active=True)

        for i in range(2):
            # Agent 3 has 2 active rooms
            Room.objects.create(user=self.agent_3, queue=self.queue, is_active=True)

        num_trials = 100
        picked_agents_results = []
        for _ in range(num_trials):
            available_agent = self.queue.get_available_agent()
            self.assertIsNotNone(
                available_agent, "get_available_agent should return an agent."
            )
            self.assertIn(available_agent, [self.agent_2, self.agent_3])
            picked_agents_results.append(available_agent)

        # Verify that both eligible agents were picked at least once over the trials.
        picked_agents_set = set(picked_agents_results)
        self.assertIn(
            self.agent_2,
            picked_agents_set,
            "Agent 2 was never picked, suggesting non-random selection.",
        )
        self.assertIn(
            self.agent_3,
            picked_agents_set,
            "Agent 3 was never picked, suggesting non-random selection.",
        )

    def test_get_available_agent_returns_random_agent_if_rooms_count_is_equal_for_general_routing_option(
        self,
    ):
        self.project.config = {"routing_option": "general"}
        self.project.save()

        for i in range(4):
            # Agent 1 has 3 active rooms
            Room.objects.create(user=self.agent_1, queue=self.queue, is_active=True)

        for i in range(2):
            # Agent 2 has 2 active rooms
            Room.objects.create(user=self.agent_2, queue=self.queue, is_active=True)

        # Agent 2 has 1 closed room
        r = Room.objects.create(user=self.agent_2, queue=self.queue)
        r.close()

        for i in range(3):
            # Agent 3 has 3 active rooms
            Room.objects.create(user=self.agent_3, queue=self.queue, is_active=True)

        num_trials = 100
        picked_agents_results = []
        for _ in range(num_trials):
            available_agent = self.queue.get_available_agent()
            self.assertIsNotNone(
                available_agent, "get_available_agent should return an agent."
            )
            self.assertIn(available_agent, [self.agent_2, self.agent_3])
            picked_agents_results.append(available_agent)

        # Verify that both eligible agents were picked at least once over the trials.
        picked_agents_set = set(picked_agents_results)
        self.assertIn(
            self.agent_2,
            picked_agents_set,
            "Agent 2 was never picked, suggesting non-random selection.",
        )
        self.assertIn(
            self.agent_3,
            picked_agents_set,
            "Agent 3 was never picked, suggesting non-random selection.",
        )


class QueueLimitPropertyTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00:00",
            work_end="17:00:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def test_limit_returns_sector_rooms_limit_when_no_group(self):
        """
        Verify if limit returns sector rooms_limit when sector is not in any group
        """
        self.assertEqual(self.queue.limit, 5)

    def test_limit_returns_group_rooms_limit_when_sector_in_active_group(self):
        """
        Verify if limit returns group rooms_limit when sector is in an active group
        """
        group_sector = GroupSector.objects.create(
            name="Test Group", project=self.project, rooms_limit=10, is_deleted=False
        )
        group_sector.sectors.add(self.sector)

        self.assertEqual(self.queue.limit, 10)

    def test_limit_returns_sector_rooms_limit_when_group_is_deleted(self):
        """
        Verify if limit returns sector rooms_limit when group is deleted
        """
        group_sector = GroupSector.objects.create(
            name="Test Group", project=self.project, rooms_limit=15, is_deleted=True
        )
        group_sector.sectors.add(self.sector)

        self.assertEqual(self.queue.limit, 5)

    def test_limit_with_multiple_groups_only_active_considered(self):
        """
        Verify if limit considers only active groups when sector has multiple group relations
        """
        deleted_group = GroupSector.objects.create(
            name="Deleted Group", project=self.project, rooms_limit=20, is_deleted=True
        )
        active_group = GroupSector.objects.create(
            name="Active Group", project=self.project, rooms_limit=12, is_deleted=False
        )

        deleted_group.sectors.add(self.sector)
        active_group.sectors.add(self.sector)

        self.assertEqual(self.queue.limit, 12)
