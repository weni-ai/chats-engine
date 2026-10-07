from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import NexusRESTClient

NEXUS_BASE_URL = "https://nexus.example.com"
PROJECT_UUID = "550e8400-e29b-41d4-a716-446655440000"


@override_settings(NEXUS_API_URL=NEXUS_BASE_URL)
@patch.object(NexusRESTClient, "get_module_token", return_value="Bearer fake-token")
class GetMultiAgentsTests(TestCase):
    def setUp(self):
        self.client_rest = NexusRESTClient()

    def test_calls_expected_url_and_headers(self, _mock_token):
        session = MagicMock()
        session.get.return_value = MagicMock(status_code=200)

        with patch.object(self.client_rest, "_get_session", return_value=session):
            response = self.client_rest.get_multi_agents(PROJECT_UUID)

        session.get.assert_called_once_with(
            url=f"{NEXUS_BASE_URL}/api/project/{PROJECT_UUID}/multi-agents",
            headers=self.client_rest.headers,
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client_rest.headers,
            {
                "Content-Type": "application/json; charset: utf-8",
                "Authorization": "Bearer fake-token",
            },
        )
