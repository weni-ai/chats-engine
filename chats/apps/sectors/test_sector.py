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
            manager=self.manager,
            rooms_limit=5,
            work_start=7,
            work_end=17,
        )
        self.sector_2 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            manager=self.manager,
            rooms_limit=5,
            work_start=7,
            work_end=17,
        )
        self.owner_auth = self.project.projectpermission_set.create(
            user=self.owner, role=1
        )
        self.manager_auth = self.sector_1.get_user_authorization(self.manager)

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = self.client.get(url, data={"project": self.project.id})
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.sector_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.uuid))

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot the sector list of the project
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.user_3_token.key)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # def
