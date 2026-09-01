from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import NexusRESTClient
from chats.apps.assisted_sales.clients import CopilotConnectClient
from chats.apps.assisted_sales.exceptions import CopilotConnectError


@override_settings(
    CONNECT_COPILOT_CREATE_URL="https://connect.example.com/copilot/create",
    NEXUS_API_URL="https://nexus.example.com",
)
@patch.object(CopilotConnectClient, "get_module_token", return_value="Bearer fake")
class CopilotConnectClientTests(TestCase):
    def setUp(self):
        self.client_rest = CopilotConnectClient()

    @patch("chats.apps.assisted_sales.clients.requests.post")
    def test_create_copilot_project(self, mock_post, _mock_token):
        mock_post.return_value = MagicMock(
            ok=True, json=lambda: {"uuid": "abc", "name": "copilot"}
        )

        data = self.client_rest.create_copilot_project("copilot", "project-uuid")

        mock_post.assert_called_once()
        self.assertEqual(data["name"], "copilot")

    @patch("chats.apps.assisted_sales.clients.requests.post")
    def test_create_copilot_project_raises_on_error(self, mock_post, _mock_token):
        mock_post.return_value = MagicMock(
            ok=False, status_code=400, text="bad", json=lambda: {"error": "invalid"}
        )

        with self.assertRaises(CopilotConnectError) as ctx:
            self.client_rest.create_copilot_project("copilot", "project-uuid")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.error, "invalid")

    @patch.object(NexusRESTClient, "get_projects_agents")
    def test_get_assigned_agents(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {
                "count": 1,
                "results": [
                    {
                        "project_uuid": "copilot-uuid",
                        "custom_agents_count": 4,
                        "official_agents_count": 2,
                        "agents": [],
                    }
                ],
            },
        )

        count = self.client_rest.get_assigned_agents("copilot-uuid")

        self.assertEqual(count, 6)
        mock_get.assert_called_once_with("copilot-uuid")

    @patch.object(NexusRESTClient, "get_projects_agents")
    def test_get_assigned_agents_returns_zero_when_project_omitted(
        self, mock_get, _mock_token
    ):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {"count": 0, "results": []},
        )

        self.assertEqual(self.client_rest.get_assigned_agents("copilot-uuid"), 0)

    @override_settings(NEXUS_API_URL="")
    def test_get_assigned_agents_returns_zero_when_url_missing(self, _mock_token):
        self.assertEqual(self.client_rest.get_assigned_agents("copilot-uuid"), 0)

    @override_settings(
        CONNECT_COPILOT_UPDATE_URL="https://connect.example.com/copilot/{uuid}"
    )
    @patch("chats.apps.assisted_sales.clients.requests.put")
    def test_update_copilot_project(self, mock_put, _mock_token):
        mock_put.return_value = MagicMock(
            ok=True, json=lambda: {"uuid": "new-uuid", "name": "copilot novo"}
        )

        data = self.client_rest.switch_copilot_project("old-uuid", "new-uuid")

        mock_put.assert_called_once()
        self.assertEqual(data["uuid"], "new-uuid")

    @override_settings(
        CONNECT_COPILOT_REMOVE_URL="https://connect.example.com/copilot/{uuid}"
    )
    @patch("chats.apps.assisted_sales.clients.requests.delete")
    def test_remove_copilot_project(self, mock_delete, _mock_token):
        mock_delete.return_value = MagicMock(ok=True)

        self.client_rest.remove_copilot_project("copilot-uuid")

        mock_delete.assert_called_once()

    @override_settings(
        CONNECT_COPILOT_LIST_URL="https://connect.example.com/org/{org_uuid}/copilot"
    )
    @patch("chats.apps.assisted_sales.clients.requests.get")
    def test_list_copilot_projects(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: [{"uuid": "abc", "name": "copilot", "assigned_agents": 3}],
        )

        data = self.client_rest.list_copilot_projects("org-uuid", name="copilot")

        mock_get.assert_called_once()
        self.assertEqual(data[0]["name"], "copilot")

    @override_settings(CONNECT_API_URL="https://connect.example.com")
    @patch("chats.apps.assisted_sales.clients.requests.get")
    def test_get_project_authorization(self, mock_get, _mock_token):
        payload = {
            "user": "member@example.com",
            "project_authorization": 3,
            "available_roles": {"3": "moderator"},
        }
        mock_get.return_value = MagicMock(ok=True, json=lambda: payload)

        data = self.client_rest.get_project_authorization(
            "project-uuid", "member@example.com"
        )

        mock_get.assert_called_once_with(
            url="https://connect.example.com/projects/project-uuid/authorization",
            headers=self.client_rest.headers,
            params={"user": "member@example.com"},
            timeout=15,
        )
        self.assertEqual(data["project_authorization"], 3)

    @override_settings(CONNECT_API_URL="https://connect.example.com")
    @patch("chats.apps.assisted_sales.clients.requests.get")
    def test_get_project_authorization_raises_on_error(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(
            ok=False,
            status_code=404,
            text="not found",
            json=lambda: {"error": "missing"},
        )

        with self.assertRaises(CopilotConnectError) as ctx:
            self.client_rest.get_project_authorization(
                "project-uuid", "member@example.com"
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.error, "missing")

    @override_settings(CONNECT_API_URL="")
    def test_get_project_authorization_raises_when_url_missing(self, _mock_token):
        with self.assertRaises(CopilotConnectError) as ctx:
            self.client_rest.get_project_authorization(
                "project-uuid", "member@example.com"
            )

        self.assertEqual(ctx.exception.status_code, 502)
