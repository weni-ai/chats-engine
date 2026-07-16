from datetime import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestBulkSendRoomsCount(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Bulk Project")
        self.other_project = Project.objects.create(name="Other Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue A", sector=self.sector)
        self.queue_b = Queue.objects.create(name="Queue B", sector=self.sector)

        self.admin = User.objects.create_user(
            email="admin@example.com", password="testpass123"
        )
        self.other_admin = User.objects.create_user(
            email="other.admin@example.com", password="testpass123"
        )
        self.attendant = User.objects.create_user(
            email="attendant@example.com", password="testpass123"
        )
        self.agent = User.objects.create_user(
            email="agent@example.com", password="testpass123"
        )
        self.agent_b = User.objects.create_user(
            email="agent.b@example.com", password="testpass123"
        )

        ProjectPermission.objects.create(
            project=self.project,
            user=self.admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.other_admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.attendant,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.url = reverse("message-bulk-send-rooms")
        self.project_uuid = str(self.project.uuid)

    def _create_room(
        self,
        *,
        queue=None,
        user=None,
        is_active=True,
        is_waiting=False,
        contact_name="C",
    ):
        contact = Contact.objects.create(name=contact_name)
        return Room.objects.create(
            queue=queue or self.queue,
            contact=contact,
            user=user,
            is_active=is_active,
            is_waiting=is_waiting,
            project_uuid=self.project_uuid,
        )

    def _get(self, user, params):
        self.client.force_authenticate(user=user)
        return self.client.get(self.url, params)

    def test_admin_can_get_count(self):
        self._create_room(user=None)
        self._create_room(user=self.agent, contact_name="Ongoing")

        response = self._get(
            self.admin,
            {
                "project": self.project_uuid,
                "status": "waiting,ongoing",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_attendant_is_forbidden(self):
        response = self._get(
            self.attendant,
            {
                "project": self.project_uuid,
                "status": "waiting",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_requires_project(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {"status": "waiting"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_status(self):
        response = self._get(
            self.admin,
            {"project": self.project_uuid},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filters_by_comma_separated_queues_and_agents(self):
        self._create_room(queue=self.queue, user=self.agent)
        self._create_room(
            queue=self.queue_b, user=self.agent_b, contact_name="Other"
        )
        self._create_room(queue=self.queue, user=None, contact_name="Waiting")

        response = self._get(
            self.admin,
            {
                "project": self.project_uuid,
                "status": "ongoing",
                "queues": f"{self.queue.uuid},{self.queue_b.uuid}",
                "agents": f"{self.agent.email},{self.agent_b.email}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_empty_queues_and_agents_count_all(self):
        self._create_room(queue=self.queue, user=None)
        self._create_room(queue=self.queue_b, user=self.agent, contact_name="Ongoing")

        response = self._get(
            self.admin,
            {
                "project": self.project_uuid,
                "status": "waiting,ongoing",
                "queues": "",
                "agents": "",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_invalid_status_returns_400(self):
        response = self._get(
            self.admin,
            {
                "project": self.project_uuid,
                "status": "closed",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_is_unauthorized(self):
        response = self.client.get(
            self.url,
            {
                "project": self.project_uuid,
                "status": "waiting",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_of_other_project_is_forbidden(self):
        response = self._get(
            self.other_admin,
            {
                "project": self.project_uuid,
                "status": "waiting",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agents_with_waiting_and_ongoing_only_counts_matching_agents(self):
        self._create_room(user=None, contact_name="Waiting")
        self._create_room(user=self.agent, contact_name="Ongoing")
        self._create_room(user=self.agent_b, contact_name="Other agent")

        response = self._get(
            self.admin,
            {
                "project": self.project_uuid,
                "status": "waiting,ongoing",
                "agents": self.agent.email,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_includes_is_waiting_rooms(self):
        self._create_room(user=None, is_waiting=True, contact_name="Flow start")
        self._create_room(user=self.agent, is_waiting=True, contact_name="Flow ongoing")

        response = self._get(
            self.admin,
            {
                "project": self.project_uuid,
                "status": "waiting,ongoing",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
