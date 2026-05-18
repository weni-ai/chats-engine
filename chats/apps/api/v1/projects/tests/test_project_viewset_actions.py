from unittest.mock import PropertyMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import (
    ContactGroupFlowReference,
    FlowStart,
    Project,
    ProjectPermission,
)
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


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
            {
                "project": "00000000-0000-0000-0000-000000000000",
                "contact": str(self.contact.external_id),
            },
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
        self.url = reverse(
            "project-list-users", kwargs={"uuid": str(self.project.uuid)}
        )
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
        self.other_project = Project.objects.create(
            name="Secondary Project", org=self.org_id
        )
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

        response = self.client.post(f"{self.url}?project={self.project.uuid}")
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
        mock_integrations.integrate_ticketer.side_effect = Exception(
            "integration failed"
        )

        response = self.client.post(f"{self.url}?project={self.project.uuid}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error integrating ticketers", response.data)


MOCK_FLOW_START_RESPONSE = {
    "uuid": "ext-flow-start-uuid",
    "flow": {"name": "Test Flow", "uuid": "flow-uuid-001"},
}


@patch("chats.apps.api.v1.projects.viewsets.FlowRESTClient")
class StartFlowTestCase(APITestCase):
    """Tests for ProjectViewset.start_flow (POST /project/{uuid}/start_flow/)"""

    def setUp(self):
        self.user, self.token = create_user_and_token("flowuser")
        self.project = Project.objects.create(
            name="Flow Project", flows_authorization="fake-token"
        )
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
            name="Flow Contact",
            external_id="ext-contact-flow-001",
        )
        self.url = reverse("project-flows", kwargs={"uuid": str(self.project.uuid)})
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.base_payload = {
            "flow": "flow-uuid-001",
            "contacts": [self.contact.external_id],
            "contact_name": "Flow Contact",
        }

    def _mock_client(self, mock_client_cls, response=None):
        mock_instance = mock_client_cls.return_value
        mock_instance.start_flow.return_value = response or MOCK_FLOW_START_RESPONSE
        return mock_instance

    # -- Permission / validation --

    def test_start_flow_without_permission_returns_401(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        other_user, other_token = create_user_and_token("nopermflow")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")

        response = self.client.post(self.url, self.base_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_start_flow_missing_flow_field_returns_400(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        payload = {
            "contacts": [self.contact.external_id],
            "contact_name": "Flow Contact",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Happy path --

    def test_start_flow_success_returns_200(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        response = self.client.post(self.url, self.base_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], "ext-flow-start-uuid")

    def test_start_flow_creates_flow_start_record(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        self.client.post(self.url, self.base_payload, format="json")

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertEqual(flow_start.flow, "flow-uuid-001")
        self.assertEqual(flow_start.permission, self.permission)
        self.assertEqual(
            flow_start.contact_data["external_id"], self.contact.external_id
        )
        self.assertEqual(flow_start.contact_data["name"], "Flow Contact")

    def test_start_flow_saves_external_id_and_name_from_response(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        self.client.post(self.url, self.base_payload, format="json")

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertEqual(flow_start.external_id, "ext-flow-start-uuid")
        self.assertEqual(flow_start.name, "Test Flow")

    def test_start_flow_creates_contact_references(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        self.client.post(self.url, self.base_payload, format="json")

        refs = ContactGroupFlowReference.objects.filter(
            flow_start__project=self.project
        )
        self.assertEqual(refs.count(), 1)
        self.assertEqual(refs.first().receiver_type, "contact")
        self.assertEqual(refs.first().external_id, self.contact.external_id)

    def test_start_flow_creates_group_references(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        payload = {
            **self.base_payload,
            "groups": ["group-uuid-001", "group-uuid-002"],
        }
        self.client.post(self.url, payload, format="json")

        refs = ContactGroupFlowReference.objects.filter(
            flow_start__project=self.project
        )
        contact_refs = refs.filter(receiver_type="contact")
        group_refs = refs.filter(receiver_type="group")
        self.assertEqual(contact_refs.count(), 1)
        self.assertEqual(group_refs.count(), 2)
        self.assertEqual(
            set(group_refs.values_list("external_id", flat=True)),
            {"group-uuid-001", "group-uuid-002"},
        )

    # -- Params forwarding --

    def test_start_flow_with_params_forwards_to_client(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        payload = {**self.base_payload, "params": {"key": "value"}}

        self.client.post(self.url, payload, format="json")

        call_args = mock_instance.start_flow.call_args
        data_sent = call_args[0][1]
        self.assertIn("params", data_sent)
        self.assertEqual(data_sent["params"], {"key": "value"})

    def test_start_flow_without_params_excludes_params_from_client(
        self, mock_client_cls
    ):
        mock_instance = self._mock_client(mock_client_cls)

        self.client.post(self.url, self.base_payload, format="json")

        call_args = mock_instance.start_flow.call_args
        data_sent = call_args[0][1]
        self.assertNotIn("params", data_sent)

    def test_start_flow_with_complex_params_forwards_intact(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        complex_params = {
            "greeting": "Hello {name}",
            "nested": {"level1": {"level2": [1, 2, 3]}},
            "tags": ["vip", "returning"],
            "priority": 5,
        }
        payload = {**self.base_payload, "params": complex_params}

        self.client.post(self.url, payload, format="json")

        call_args = mock_instance.start_flow.call_args
        data_sent = call_args[0][1]
        self.assertEqual(data_sent["params"], complex_params)

    def test_start_flow_params_not_persisted_in_flow_start_model(self, mock_client_cls):
        """params are forwarded to the external API, not stored in FlowStart."""
        self._mock_client(mock_client_cls)
        payload = {**self.base_payload, "params": {"key": "value"}}

        self.client.post(self.url, payload, format="json")

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertNotIn("params", flow_start.contact_data)

    # -- Room-related --

    def test_start_flow_room_with_existing_active_flowstart_returns_400(
        self, mock_client_cls
    ):
        self._mock_client(mock_client_cls)
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        FlowStart.objects.create(
            project=self.project,
            permission=self.permission,
            room=room,
            is_deleted=False,
        )
        payload = {**self.base_payload, "room": str(room.pk)}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(Room, "notify_room")
    @patch.object(Room, "request_callback")
    @patch.object(Room, "is_24h_valid", new_callable=PropertyMock, return_value=False)
    def test_start_flow_room_not_24h_valid_links_room_and_sets_waiting(
        self, _mock_24h, mock_callback, mock_notify, mock_client_cls
    ):
        self._mock_client(mock_client_cls)
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        payload = {**self.base_payload, "room": str(room.pk)}

        self.client.post(self.url, payload, format="json")

        room.refresh_from_db()
        self.assertTrue(room.is_waiting)
        mock_callback.assert_called_once()

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertEqual(flow_start.room, room)

    @patch.object(Room, "notify_room")
    @patch.object(Room, "is_24h_valid", new_callable=PropertyMock, return_value=True)
    def test_start_flow_room_24h_valid_does_not_link_room(
        self, _mock_24h, mock_notify, mock_client_cls
    ):
        self._mock_client(mock_client_cls)
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        payload = {**self.base_payload, "room": str(room.pk)}

        self.client.post(self.url, payload, format="json")

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertIsNone(flow_start.room)

    @patch("chats.apps.api.v1.projects.viewsets.create_room_feedback_message")
    @patch.object(Room, "notify_room")
    @patch.object(Room, "request_callback")
    @patch.object(Room, "is_24h_valid", new_callable=PropertyMock, return_value=False)
    def test_start_flow_with_room_creates_feedback_message(
        self, _mock_24h, mock_callback, mock_notify, mock_feedback, mock_client_cls
    ):
        self._mock_client(mock_client_cls)
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        payload = {**self.base_payload, "room": str(room.pk)}

        self.client.post(self.url, payload, format="json")

        mock_feedback.assert_called_once()
        call_kwargs = mock_feedback.call_args
        self.assertEqual(call_kwargs[0][0], room)
        self.assertEqual(call_kwargs[1]["method"], "fs")

    def test_start_flow_without_room_does_not_create_feedback(self, mock_client_cls):
        self._mock_client(mock_client_cls)

        with patch(
            "chats.apps.api.v1.projects.viewsets.create_room_feedback_message"
        ) as mock_feedback:
            self.client.post(self.url, self.base_payload, format="json")
            mock_feedback.assert_not_called()
