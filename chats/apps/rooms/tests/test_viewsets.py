from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_contact, create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.queues.models import Queue, QueueAuthorization


class RoomTests(APITestCase):
    def setUp(self):
        # USERS
        self.owner, self.owner_token = create_user_and_token("owner")

        self.manager, self.manager_token = create_user_and_token("manager")
        self.manager_2, self.manager_2_token = create_user_and_token("manager")
        self.manager_3, self.manager_3_token = create_user_and_token("manager 3")

        self.agent, self.agent_token = create_user_and_token("agent")
        self.agent_2, self.agent_2_token = create_user_and_token("agent2")

        # CONTACTS
        self.contact = create_contact("Contact", "contatc@mail.com", "offline", {})
        self.contact_2 = create_contact("Contact2", "contatc2@mail.com", "offline", {})
        self.contact_3 = create_contact("Contact3", "contatc3@mail.com", "offline", {})

        # PROJECTS
        self.project = Project.objects.create(name="Test Project")
        self.project_2 = Project.objects.create(name="Test Project")

        # PROJECT AUTHORIZATIONS
        self.owner_auth = self.project.permissions.create(
            user=self.owner, role=ProjectPermission.ROLE_ADMIN
        )

        self.manager_perm = self.project.permissions.get(user=self.owner)
        self.manager2_perm = self.project.permissions.get(user=self.owner)
        self.agent_perm = self.project.permissions.create(
            user=self.agent, role=ProjectPermission.ROLE_ATTENDANT
        )
        self.agent2_perm = self.project.permissions.create(
            user=self.agent_2, role=ProjectPermission.ROLE_ATTENDANT
        )

        # SECTORS
        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_2 = Sector.objects.get(
            name="Test Sector",
            project=self.project,
        )
        self.sector_3 = Sector.objects.create(
            name="Sector on project 2",
            project=self.project_2,
            rooms_limit=1,
            work_start="07:00",
            work_end="17:00",
        )

        # SECTOR AUTHORIZATIONS
        self.manager_auth = self.sector_1.set_user_authorization(
            self.manager_perm, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth = self.sector_2.set_user_authorization(
            self.manager2_perm, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth_1 = self.sector_3.set_user_authorization(
            self.manager_perm, role=SectorAuthorization.ROLE_MANAGER
        )

        # QUEUES
        self.queue_1 = Queue.objects.create(name="Q1", sector=self.sector_1)
        self.queue_2 = Queue.objects.create(name="Q2", sector=self.sector_1)
        self.queue_3 = Queue.objects.create(name="Q3", sector=self.sector_2)

        # QUEUE AUTHORIZATIONS
        self.agent_1_auth = self.queue_1.authorizations.create(
            permission=self.agent_perm, role=QueueAuthorization.ROLE_AGENT
        )
        self.agent_2_auth = self.queue_2.authorizations.create(
            permission=self.agent2_perm, role=QueueAuthorization.ROLE_AGENT
        )
        self.agent_2_auth_2 = self.queue_3.authorizations.create(
            permission=self.agent2_perm, role=QueueAuthorization.ROLE_AGENT
        )

        # ROOMS
        self.room_1 = Room.objects.create(
            contact=self.contact, queue=self.queue_1, user=self.agent
        )
        self.room_2 = Room.objects.create(contact=self.contact_2, queue=self.queue_2)
        self.room_3 = Room.objects.create(contact=self.contact_3, queue=self.queue_3)

    def _request_list_rooms(self, token, data: dict):
        url = reverse("room-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = client.get(url, data=data)
        results = response.json().get("results")
        return response, results

    def _ok_list_rooms(self, token, rooms: list, data: dict):
        response, results = self._request_list_rooms(token, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), len(rooms))
        for result in results:
            self.assertIn(result.get("uuid"), rooms)

    def _not_ok_list_rooms(self, token, data: dict):
        response, _ = self._request_list_rooms(token, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 0)

    def test_list_rooms_given_agents(self):
        self._ok_list_rooms(
            self.agent_token,
            [str(self.room_1.uuid)],
            {"project": self.project.uuid},
        )
        self._ok_list_rooms(
            self.agent_2_token,
            [str(self.room_2.uuid), str(self.room_3.uuid)],
            {"project": self.project.uuid},
        )

    def test_list_rooms_with_manager_and_admin_token(self):
        self._ok_list_rooms(
            self.manager_token,
            [str(self.room_1.uuid), str(self.room_2.uuid)],
            {"project": self.project.uuid},
        )

        self._ok_list_rooms(
            self.owner_token,
            [str(self.room_1.uuid), str(self.room_2.uuid), str(self.room_3.uuid)],
            {"project": self.project.uuid},
        )

    def test_list_rooms_with_not_permitted_manager_token(self):
        self._not_ok_list_rooms(
            self.manager_3_token,
            {"project": self.project.uuid},
        )
