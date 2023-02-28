from django.test import TestCase

from django.db import IntegrityError
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model

from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector


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
        self.room = Room.objects.create(
            contact=self.contact, is_active=True, queue=self.queue
        )


class QueueAvailableAgentsTestCase(QueueSetUpMixin, TestCase):
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
