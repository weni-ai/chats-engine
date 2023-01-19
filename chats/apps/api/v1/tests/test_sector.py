from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from chats.apps.accounts.models import User

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.rooms.models import Room
from rest_framework.authtoken.models import Token


class SectorTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token =  Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')
        self.sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.sector_2 = Sector.objects.get(pk='4f88b656-194d-4a83-a166-5d84ba825b8d')
        self.wrong_user = User.objects.get(pk=1)
        self.wrong_login_token =  Token.objects.get_or_create(user=self.wrong_user)[0]

    def test_retrieve_sector_with_right_project_token(self):
        """
        Verify if the list endpoint for sector its returning the correct object.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url, data={"project": self.project.pk})
        results = response.json().get("results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(results[0].get("uuid"), str(self.sector.pk))
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.pk))

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot access the sector list of the project
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.wrong_login_token.key)
        response = client.get(url, data={"project": self.project.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_with_right_project_token(self):
        """
        Verify if the Project Permission its returning the correct value from first_access field.
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(self.project.pk),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_with_right_project_token(self):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.put(url, data={"name": "sector 2 updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.assertEqual("sector 2 updated", sector.name)

    def test_delete_sector_with_right_project_token(self):
        """
        Verify if the endpoint for delete sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["is_deleted"], True)
