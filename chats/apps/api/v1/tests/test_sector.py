"""
    TestCases
    GET
        1 
        2
        3
        4
        5
    LIST
    PUT
    POST
    DELETE
"""
from django.urls import include, path, reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from chats.apps.api.utils import create_message, create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector, SectorAuthorization


class SectorTests(APITestCase):
    def setUp(self):
        self.owner, self.owner_token = create_user_and_token("owner")
        self.manager, self.manager_token = create_user_and_token("manager")
        self.user, self.user_token = create_user_and_token("user")
        self.user_2, self.user_2_token = create_user_and_token("user2")
        self.user_3, self.user_3_token = create_user_and_token("user3")

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

        self.sector_3 = Sector.objects.create(
            name="Test Sector",
            project=self.project_2,
            rooms_limit=3,
            work_start="07:00",
            work_end="17:00",
        )

        self.owner_auth = self.project.authorizations.create(user=self.owner, role=1)
        self.manager_auth = self.sector_1.set_user_authorization(self.manager, role=2)
        self.manager_2_auth = self.sector_2.set_user_authorization(self.manager, role=2)
        self.manager_3_auth = self.sector_3.set_user_authorization(self.user_3, role=2)

    def test_retrieve_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.get(url, data={"project": self.project.uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.get(url, data={"project": self.project.uuid})
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.sector_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.uuid))

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot access the sector list of the project
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.user_3_token.key)
        response = client.get(url, data={"project": self.project.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 0)

        response = self.client.get(url, data={"project": self.project.uuid})

    def test_create_sector_with_right_project_token(self):
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(self.project.uuid),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.put(url, data={"name": "sector 2 updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(uuid=self.sector_1.uuid)

        self.assertEqual(response.data.get("name"), sector.name)
