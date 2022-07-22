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
    def setup(self):
        self.owner, self.owner_token = create_user_and_token("owner")
        self.manager, self.manager_token = create_user_and_token("manager")
        self.user, self.user_token = create_user_and_token("user")
        self.user_2, self.user_2_token = create_user_and_token("user2")

        self.project = Project.objects.create(
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
        self.owner_auth, created = self.project.projectpermission_set.create(
            user=self.owner, role=1
        )
        self.manager_auth, created = self.sector_1.get_user_authorization(self.manager)

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure we can create a new account object.
        """
        url = reverse("sector-list") + "?project=Lol"
        print(url)
        import pdb

        pdb.set_trace()
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = self.client.get(
            url,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # self.assertEqual(response.)
