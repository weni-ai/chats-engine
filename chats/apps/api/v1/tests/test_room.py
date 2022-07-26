from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_contact, create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization


class RoomTests(APITestCase):
    def setUp(self):
        self.owner, self.owner_token = create_user_and_token("owner")

        self.manager, self.manager_token = create_user_and_token("manager")

        self.agent, self.agent_token = create_user_and_token("agent")
        self.agent_2, self.agent_2_token = create_user_and_token("agent2")

        self.contact = create_contact("Contact", "contatc@mail.com")
        self.contact_2 = create_contact("Contact2", "contatc2@mail.com")
        self.contact_3 = create_contact("Contact3", "contatc2@mail.com")

        self.project = Project.objects.create(
            name="Test Project", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.project_2 = Project.objects.create(
            name="Test Project", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_2 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="07:00",
            work_end="17:00",
        )

        self.room_1 = Room.objects.create(
            contact=self.contact, sector=self.sector_1, user=self.agent
        )

        self.room_2 = Room.objects.create(contact=self.contact_2, sector=self.sector_1)

        self.room_3 = Room.objects.create(contact=self.contact_3, sector=self.sector_2)

        self.owner_auth = self.project.authorizations.create(
            user=self.owner, role=ProjectPermission.ROLE_ADMIN
        )
        self.manager_auth = self.sector_1.set_user_authorization(
            self.manager, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth = self.sector_2.set_user_authorization(
            self.manager, role=SectorAuthorization.ROLE_MANAGER
        )
        self.agent_auth = self.sector_1.set_user_authorization(
            self.agent, role=SectorAuthorization.ROLE_AGENT
        )

    def list_rooms_with_agent_token(self):
        url = reverse("rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.agent_token.key)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.sector_1.uuid))
