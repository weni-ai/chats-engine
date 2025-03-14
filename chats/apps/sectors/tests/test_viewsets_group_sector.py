from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization, Sector


class GroupSectorTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.sector_2 = Sector.objects.get(pk="4f88b656-194d-4a83-a166-5d84ba825b8d")
        self.wrong_user = User.objects.get(pk=1)
        self.wrong_login_token = Token.objects.get_or_create(user=self.wrong_user)[0]

        # Create a test group sector
        self.group_sector = GroupSector.objects.create(
            name="Test Group", project=self.project, rooms_limit=10
        )

    def test_create_group_sector(self):
        """
        Verify if creating a group sector works correctly
        """
        url = reverse("group_sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {"name": "New Group", "project": str(self.project.pk), "rooms_limit": 5}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Group")

    def test_retrieve_group_sector(self):
        """
        Verify if retrieving a group sector works correctly
        """
        url = reverse("group_sector-detail", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Group")

    def test_list_group_sectors_with_project(self):
        """
        Verify if listing group sectors with project filter works correctly
        """
        url = reverse("group_sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        # Delete all existing group sectors for this project
        GroupSector.objects.filter(project=self.project).delete()

        # Create a new group sector
        GroupSector.objects.create(
            name="Additional Test Group", project=self.project, rooms_limit=10
        )

        response = client.get(url, {"project": str(self.project.pk)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)  # Should be exactly 1

    def test_update_group_sector(self):
        """
        Verify if updating a group sector works correctly
        """
        url = reverse("group_sector-detail", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {"name": "Updated Group", "rooms_limit": 15}
        response = client.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Group")

    def test_add_sector_to_group(self):
        """
        Verify if adding a sector to a group works correctly
        """
        url = reverse("group_sector-add-sector", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {"sector": str(self.sector.pk)}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_invalid_sector_to_group(self):
        """
        Verify if adding an invalid sector to a group fails
        """
        url = reverse("group_sector-add-sector", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {"sector": "invalid-sector-uuid"}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dont_pass_sector_to_add_sector(self):
        """
        Verify if not passing a sector to add a sector to a group fails
        """
        url = reverse("group_sector-add-sector", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        data = {}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_sector_from_group(self):
        """
        Verify if removing a sector from a group works correctly
        """
        self.group_sector.sectors.add(self.sector)

        url = reverse("group_sector-remove-sector", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {"sector": str(self.sector.pk)}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_remove_invalid_sector_from_group(self):
        """
        Verify if removing an invalid sector from a group fails
        """
        url = reverse("group_sector-remove-sector", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        data = {"sector": "invalid-sector-uuid"}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dont_pass_sector_to_remove_sector(self):
        """
        Verify if not passing a sector to remove a sector from a group fails
        """
        url = reverse("group_sector-remove-sector", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        data = {}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_group_sector(self):
        """
        Verify if deleting a group sector works correctly
        """
        url = reverse("group_sector-detail", args=[self.group_sector.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class GroupSectorAuthorizationTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.wrong_user = User.objects.get(pk=1)
        self.wrong_login_token = Token.objects.get_or_create(user=self.wrong_user)[0]

        # Create a test group sector
        self.group_sector = GroupSector.objects.create(
            name="Test Group", project=self.project, rooms_limit=10
        )

    def test_create_group_sector_authorization(self):
        """
        Verify if creating a group sector authorization works correctly
        """
        url = reverse("group_sector_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        # Create a project permission first
        project_permission = ProjectPermission.objects.get(
            project=self.project, user=self.manager_user, role=1  # 1 = Manager role
        )

        data = {
            "group_sector": str(self.group_sector.uuid),
            "permission": str(project_permission.uuid),
            "role": GroupSectorAuthorization.ROLE_MANAGER,
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_group_sector_authorization_invalid_role(self):
        """
        Verify if creating a group sector authorization with invalid role fails
        """
        url = reverse("group_sector_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {
            "group_sector": str(self.group_sector.uuid),
            "permission": "ce3f052c-e71d-402c-b02e-1dfaca8b3d45",  # From fixture
            "role": 3,  # Invalid role
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_group_sector_authorization_without_role_and_permission(self):
        """
        Verify if creating a group sector authorization without role and permission fails
        """
        url = reverse("group_sector_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {
            "group_sector": str(self.group_sector.uuid),
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_group_sector_authorizations(self):
        """
        Verify if listing group sector authorizations works correctly
        """
        url = reverse("group_sector_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url, {"group_sector": str(self.group_sector.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_group_sector_authorization(self):
        """
        Verify if deleting a group sector authorization works correctly
        """
        # Create a project permission first
        project_permission = ProjectPermission.objects.get(
            project=self.project, user=self.manager_user, role=1  # 1 = Manager role
        )

        group_sector_auth = GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=project_permission,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )
        url = reverse("group_sector_auth-detail", args=[group_sector_auth.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_group_sector_authorization_invalid_uuid(self):
        """
        Verify if deleting a group sector authorization with invalid uuid fails
        """
        url = reverse("group_sector_auth-detail", args=["invalid-uuid"])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
