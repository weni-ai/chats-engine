from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.assisted_sales.exceptions import CopilotConnectError
from chats.apps.assisted_sales.models import CopilotIntegration
from chats.apps.projects.models import Project, ProjectPermission


@override_settings(
    CONNECT_COPILOT_CREATE_URL="https://connect.example.com/copilot/create",
    CONNECT_COPILOT_AGENTS_COUNT_URL="https://connect.example.com/copilot/{uuid}/agents",
    WENI_WEBCHAT_HOST="https://flows.weni.ai",
    WENI_WEBCHAT_SOCKET_URL="wss://websocket.weni.ai",
)
class CopilotProjectCreateViewTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("edu")
        self.user.first_name = "edu"
        self.user.save(update_fields=["first_name"])
        self.project = Project.objects.create(name="Live Desk", timezone="UTC")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = "/v1/project/copilot/create"
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def _connect_payload(self):
        return {
            "uuid": str(uuid4()),
            "name": "projeto copilot teste",
            "created_on": "2026-08-12T12:00:00Z",
            "channel_uuid": str(uuid4()),
        }

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_create_copilot_integration(self, mock_client_cls):
        connect_data = self._connect_payload()
        mock_client = MagicMock()
        mock_client.create_copilot_project.return_value = connect_data
        mock_client.get_assigned_agents.return_value = 5
        mock_client_cls.return_value = mock_client

        response = self.client.post(
            self.url,
            {"name": "projeto copilot teste", "project": str(self.project.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "projeto copilot teste")
        self.assertEqual(response.data["assigned_agents"], 5)
        self.assertEqual(response.data["connected_by"], "edu")
        integration = CopilotIntegration.objects.get(uuid=response.data["uuid"])
        self.assertEqual(integration.assigned_agents, 5)
        self.assertEqual(str(integration.copilot_project_uuid), connect_data["uuid"])
        self.assertEqual(integration.connection["connectOn"], "mount")
        self.assertEqual(
            integration.connection["channelUuid"], connect_data["channel_uuid"]
        )
        mock_client.create_copilot_project.assert_called_once()

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_create_fails_when_connect_fails(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.create_copilot_project.side_effect = CopilotConnectError(
            status_code=502, error="Connect unavailable"
        )
        mock_client_cls.return_value = mock_client

        response = self.client.post(
            self.url,
            {"name": "projeto copilot teste", "project": str(self.project.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["error"], "Connect unavailable")
        self.assertFalse(CopilotIntegration.objects.exists())

    def test_create_forbidden_without_permission(self):
        other, other_token = create_user_and_token("other")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")

        response = self.client.post(
            self.url,
            {"name": "projeto copilot teste", "project": str(self.project.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CopilotIntegration.objects.exists())

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_create_rejects_duplicate_integration(self, mock_client_cls):
        CopilotIntegration.objects.create(
            project=self.project,
            copilot_project_uuid=uuid4(),
            name="existing",
            assigned_agents=1,
            connected_by=self.user,
        )

        response = self.client.post(
            self.url,
            {"name": "projeto copilot teste", "project": str(self.project.uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_client_cls.return_value.create_copilot_project.assert_not_called()


@override_settings(
    CONNECT_COPILOT_UPDATE_URL="https://connect.example.com/copilot/{uuid}",
    CONNECT_COPILOT_AGENTS_COUNT_URL="https://connect.example.com/copilot/{uuid}/agents",
)
class CopilotProjectUpdateViewTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("edu")
        self.user.first_name = "edu"
        self.user.save(update_fields=["first_name"])
        self.project = Project.objects.create(name="Live Desk", timezone="UTC")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.old_copilot_uuid = uuid4()
        self.new_copilot_uuid = uuid4()
        self.integration = CopilotIntegration.objects.create(
            project=self.project,
            copilot_project_uuid=self.old_copilot_uuid,
            name="copilot antigo",
            assigned_agents=2,
            connected_by=self.user,
        )
        self.url = f"/v1/project/copilot/update/{self.integration.uuid}"
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_update_copilot_integration(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.switch_copilot_project.return_value = {
            "uuid": str(self.new_copilot_uuid),
            "name": "copilot novo",
            "channel_uuid": str(uuid4()),
        }
        mock_client.get_assigned_agents.return_value = 7
        mock_client_cls.return_value = mock_client

        response = self.client.put(
            self.url, {"new_uuid": str(self.new_copilot_uuid)}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "copilot novo")
        self.assertEqual(response.data["assigned_agents"], 7)
        self.assertEqual(str(response.data["uuid"]), str(self.integration.uuid))
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.name, "copilot novo")
        self.assertEqual(self.integration.copilot_project_uuid, self.new_copilot_uuid)
        self.assertEqual(self.integration.assigned_agents, 7)

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_update_fails_when_connect_fails(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.switch_copilot_project.side_effect = CopilotConnectError(
            status_code=502, error="Connect unavailable"
        )
        mock_client_cls.return_value = mock_client

        response = self.client.put(
            self.url, {"new_uuid": str(self.new_copilot_uuid)}, format="json"
        )

        self.assertEqual(response.status_code, 502)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.copilot_project_uuid, self.old_copilot_uuid)

    def test_update_forbidden_without_permission(self):
        _, other_token = create_user_and_token("other")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")

        response = self.client.put(
            self.url, {"new_uuid": str(self.new_copilot_uuid)}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CopilotProjectRemoveViewTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("edu")
        self.project = Project.objects.create(name="Live Desk", timezone="UTC")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.integration = CopilotIntegration.objects.create(
            project=self.project,
            copilot_project_uuid=uuid4(),
            name="copilot",
            assigned_agents=2,
            connected_by=self.user,
        )
        self.url = f"/v1/project/copilot/remove/{self.integration.uuid}"
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_remove_copilot_integration(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": 200})
        self.assertFalse(
            CopilotIntegration.objects.filter(uuid=self.integration.uuid).exists()
        )
        mock_client.remove_copilot_project.assert_called_once()

    @patch("chats.apps.assisted_sales.usecases.CopilotConnectClient")
    def test_remove_fails_when_connect_fails(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.remove_copilot_project.side_effect = CopilotConnectError(
            status_code=502, error="Connect unavailable"
        )
        mock_client_cls.return_value = mock_client

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 502)
        self.assertTrue(
            CopilotIntegration.objects.filter(uuid=self.integration.uuid).exists()
        )

    def test_remove_forbidden_without_permission(self):
        _, other_token = create_user_and_token("other")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            CopilotIntegration.objects.filter(uuid=self.integration.uuid).exists()
        )
