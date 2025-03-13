from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorTag


class SectorTagTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.manager_user = User.objects.get(pk=8)
        self.manager_token = Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token = Token.objects.get(user=self.agent_user)

        self.tag_1 = self.sector.tags.create(name="tag 1")
        self.tag_2 = self.sector.tags.create(name="tag 2")

    def list_sector_tag_with_token(self, token, filter_by_sector=True):
        """
        Verify if the list endpoint for sector tag its returning the correct object.
        """
        url = reverse("sectortag-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)

        data = {"sector": self.sector.pk} if filter_by_sector else {}

        response = client.get(url, data=data)
        return response

    def test_list_sector_tags_with_manager_token(self):
        """
        Verify if the list endpoint for sector tag its returning the correct object using manager token.
        """
        response = self.list_sector_tag_with_token(self.manager_token.key)
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.tag_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.tag_2.uuid))

    def test_list_sector_tags_with_agent_token(self):
        """
        Verify if the list endpoint for sector tag its returning the correct object using agent token.
        """
        response = self.list_sector_tag_with_token(self.agent_token.key)
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.tag_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.tag_2.uuid))

    def test_retrieve_sector_tags_with_manager_token(self):
        """
        Verify if the retrieve endpoint for sector tag its returning the correct object passing manager token.
        """
        url = reverse("sectortag-detail", args=[self.tag_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.get(url, data={"sector": self.sector.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_tags_with_manager_token(self):
        """
        Verify if the create endpoint for sector tag it's working as expected using manager token.
        """
        url = reverse("sectortag-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 123",
            "sector": str(self.sector.uuid),
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_tags_with_manager_token(self):
        """
        Verify if the update endpoint for sector tag it's working as expected using manager token.
        """
        url = reverse("sectortag-detail", args=[self.tag_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 12222223",
        }
        response = client.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_sector_tags_with_manager_token(self):
        """
        Verify if the delete endpoint for sector tag it's working as expected using manager token.
        """
        url = reverse("sectortag-detail", args=[self.tag_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_list_sector_tags_from_other_projects(self):
        """
        Verify if the list endpoint for sector tags only returns tags from projects the user has access to.
        """
        project = Project.objects.create(name="project 3")
        sector = Sector.objects.create(
            name="sector 3",
            project=project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        tag = SectorTag.objects.create(name="tag 3", sector=sector)

        response = self.list_sector_tag_with_token(
            self.manager_token.key, filter_by_sector=False
        )
        results = response.json().get("results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tags_uuids = [result.get("uuid") for result in results]

        self.assertNotIn(str(tag.uuid), tags_uuids)

    def test_list_sector_tags_with_internal_token(self):
        """
        Verify if the list endpoint for sector tags returns all tags when the user has internal permission.
        """
        project = Project.objects.create(name="project 3")
        sector = Sector.objects.create(
            name="sector 3",
            project=project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        tag = SectorTag.objects.create(name="tag 3", sector=sector)

        user = User.objects.create(
            email="teste@teste.com",
            password="teste",
            is_staff=True,
        )
        token = Token.objects.create(user=user)
        perm = Permission.objects.create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        user.user_permissions.add(perm)

        response = self.list_sector_tag_with_token(token.key, filter_by_sector=False)
        results = response.json().get("results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tags_uuids = [result.get("uuid") for result in results]

        self.assertIn(str(tag.uuid), tags_uuids)
