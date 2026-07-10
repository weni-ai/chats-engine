from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector


class ProjectViewsetListRetrieveTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("projuser")
        self.project = Project.objects.create(name="List Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.other = Project.objects.create(name="Other Project")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_returns_accessible_projects(self):
        url = reverse("project-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn(self.project.name, names)
        self.assertNotIn(self.other.name, names)

    def test_retrieve_project(self):
        url = reverse("project-detail", kwargs={"uuid": self.project.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.project.name)

    def test_can_trigger_flows(self):
        Sector.objects.create(
            name="Flow Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            can_trigger_flows=True,
        )
        url = reverse("project-can_trigger_flows", kwargs={"uuid": self.project.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["can_trigger_flows"])

    @patch("chats.apps.api.v1.projects.viewsets.FlowRESTClient")
    def test_list_contacts(self, mock_client_cls):
        mock_client_cls.return_value.list_contacts.return_value = {
            "results": [{"uuid": "c1", "name": "Contact"}]
        }
        url = reverse("project-contacts", kwargs={"uuid": self.project.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_client_cls.return_value.list_contacts.assert_called_once()
