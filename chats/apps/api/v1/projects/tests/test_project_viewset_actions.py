from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.api.utils import create_user_and_token


class RetrieveFlowWarningTestCase(APITestCase):
    """Tests for ProjectViewset.retrieve_flow_warning (GET /project/retrieve_flow_warning/)"""

    def setUp(self):
        self.user, self.token = create_user_and_token("warnuser")
        self.project = Project.objects.create(name="Warning Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            name="Contact",
            external_id="ext-contact-uuid-001",
        )
        self.url = reverse("project-verify-flow-start")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_project_not_found_returns_404(self):
        response = self.client.get(
            self.url,
            {"project": "00000000-0000-0000-0000-000000000000", "contact": str(self.contact.external_id)},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("project", response.data)

    def test_contact_not_found_returns_404(self):
        response = self.client.get(
            self.url,
            {"project": str(self.project.uuid), "contact": "nonexistent-ext-id"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("contact", response.data)

    def test_no_active_room_returns_show_warning_false(self):
        response = self.client.get(
            self.url,
            {"project": str(self.project.uuid), "contact": self.contact.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["show_warning"])

    def test_active_room_with_user_returns_agent_name(self):
        agent, _ = create_user_and_token("agentflow")
        agent.first_name = "Alice"
        agent.save()
        Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=agent,
            is_active=True,
        )
        response = self.client.get(
            self.url,
            {"project": str(self.project.uuid), "contact": self.contact.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["show_warning"])
        self.assertEqual(response.data["agent"], "Alice")
        self.assertEqual(response.data["queue"], self.queue.name)

    def test_active_room_without_user_returns_show_warning_true_without_agent(self):
        Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        response = self.client.get(
            self.url,
            {"project": str(self.project.uuid), "contact": self.contact.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["show_warning"])
        self.assertNotIn("agent", response.data)
        self.assertEqual(response.data["queue"], self.queue.name)

    def test_unauthenticated_request_returns_401(self):
        self.client.credentials()
        response = self.client.get(
            self.url,
            {"project": str(self.project.uuid), "contact": self.contact.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ListUsersTestCase(APITestCase):
    """Tests for ProjectViewset.list_users (GET /project/{uuid}/list_users/)"""

    def setUp(self):
        self.user, self.token = create_user_and_token("listuser")
        self.project = Project.objects.create(name="Users Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse("project-list-users", kwargs={"uuid": str(self.project.uuid)})
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_users_returns_project_permissions(self):
        extra_user, _ = create_user_and_token("extra")
        ProjectPermission.objects.create(
            project=self.project,
            user=extra_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 2 users: self.user + extra_user
        self.assertEqual(response.data["count"], 2)

    def test_list_users_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users_without_project_permission_returns_404(self):
        other_user, other_token = create_user_and_token("nopermprojuser")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SetProjectAsPrincipalTestCase(APITestCase):
    """Tests for ProjectViewset.set_project_as_principal (POST /project/{uuid}/set-project-principal/)"""

    def setUp(self):
        self.user, self.token = create_user_and_token("principaluser")
        self.org_id = "org-test-001"
        self.project = Project.objects.create(name="Main Project", org=self.org_id)
        self.other_project = Project.objects.create(name="Secondary Project", org=self.org_id)
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse(
            "project-set-project-as-principal", kwargs={"uuid": str(self.project.uuid)}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_set_as_principal_returns_200(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_set_as_principal_sets_flag_on_project(self):
        self.client.post(self.url)
        self.project.refresh_from_db()
        self.assertTrue(self.project.config.get("its_principal"))

    def test_set_as_principal_unsets_flag_on_other_org_projects(self):
        self.client.post(self.url)
        self.other_project.refresh_from_db()
        self.assertFalse(self.other_project.config.get("its_principal"))

    def test_set_as_principal_without_permission_returns_404(self):
        other_user, other_token = create_user_and_token("noprincipal")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_as_principal_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ListDiscussionSectorTestCase(APITestCase):
    """Tests for ProjectViewset.list_discussion_sector (GET /project/{uuid}/list_discussion_sector/)"""

    def setUp(self):
        self.user, self.token = create_user_and_token("sectorlistuser")
        self.project = Project.objects.create(name="Discussion Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse(
            "project-list-sectors", kwargs={"uuid": str(self.project.uuid)}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_returns_sectors_for_project(self):
        Sector.objects.create(
            name="Sector A",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        Sector.objects.create(
            name="Sector B",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_does_not_return_sectors_from_other_projects(self):
        other_project = Project.objects.create(name="Other Project")
        Sector.objects.create(
            name="Other Sector",
            project=other_project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        Sector.objects.create(
            name="My Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "My Sector")

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IntegrateSectorsTestCase(APITestCase):
    """Tests for ProjectViewset.integrate_sectors (POST /project/integrate_sectors/)"""

    def setUp(self):
        self.user, self.token = create_user_and_token("integrateuser")
        self.project = Project.objects.create(name="Integrate Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse("project-integrate_sectors")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("chats.apps.api.v1.projects.viewsets.IntegratedTicketers")
    def test_integrate_sectors_returns_200_on_success(self, mock_integrations_cls):
        mock_integrations = mock_integrations_cls.return_value
        mock_integrations.integrate_ticketer.return_value = None
        mock_integrations.integrate_topic.return_value = None

        response = self.client.post(
            f"{self.url}?project={self.project.uuid}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_integrate_sectors_project_not_found_returns_404(self):
        response = self.client.post(
            f"{self.url}?project=00000000-0000-0000-0000-000000000000"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("project", response.data)

    @patch("chats.apps.api.v1.projects.viewsets.IntegratedTicketers")
    def test_integrate_sectors_exception_returns_400(self, mock_integrations_cls):
        mock_integrations = mock_integrations_cls.return_value
        mock_integrations.integrate_ticketer.side_effect = Exception("integration failed")

        response = self.client.post(
            f"{self.url}?project={self.project.uuid}"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error integrating ticketers", response.data)
