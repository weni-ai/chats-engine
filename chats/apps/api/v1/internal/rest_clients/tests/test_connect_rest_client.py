from uuid import uuid4
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from chats.apps.api.v1.internal.rest_clients.connect_rest_client import (
    ConnectRESTClient,
)


CONNECT_BASE_URL = "https://connect.example.com"


@override_settings(CONNECT_API_URL=CONNECT_BASE_URL)
@patch.object(ConnectRESTClient, "get_module_token", return_value="Bearer fake-token")
class TestListChannels(TestCase):
    def setUp(self):
        self.client_rest = ConnectRESTClient()
        self.project_uuid = uuid4()

    @patch("chats.apps.api.v1.internal.rest_clients.connect_rest_client.requests.get")
    def test_list_channels(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(status_code=200)

        response = self.client_rest.list_channels(
            project_uuid=self.project_uuid,
            channel_type="whatsapp",
        )

        mock_get.assert_called_once_with(
            url=f"{CONNECT_BASE_URL}/v2/projects/channels",
            headers=self.client_rest.headers,
            params={
                "project_uuid": str(self.project_uuid),
                "channel_type": "whatsapp",
            },
        )
        self.assertEqual(response.status_code, 200)

    @patch("chats.apps.api.v1.internal.rest_clients.connect_rest_client.requests.get")
    def test_list_channels_with_exclude_wpp_demo(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(status_code=200)

        response = self.client_rest.list_channels(
            project_uuid=self.project_uuid,
            channel_type="whatsapp",
            exclude_wpp_demo=True,
        )

        mock_get.assert_called_once_with(
            url=f"{CONNECT_BASE_URL}/v2/projects/channels",
            headers=self.client_rest.headers,
            params={
                "project_uuid": str(self.project_uuid),
                "channel_type": "whatsapp",
                "exclude_wpp_demo": True,
            },
        )
        self.assertEqual(response.status_code, 200)

    @patch("chats.apps.api.v1.internal.rest_clients.connect_rest_client.requests.get")
    def test_list_channels_exclude_wpp_demo_false(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(status_code=200)

        self.client_rest.list_channels(
            project_uuid=self.project_uuid,
            channel_type="whatsapp",
            exclude_wpp_demo=False,
        )

        mock_get.assert_called_once_with(
            url=f"{CONNECT_BASE_URL}/v2/projects/channels",
            headers=self.client_rest.headers,
            params={
                "project_uuid": str(self.project_uuid),
                "channel_type": "whatsapp",
                "exclude_wpp_demo": False,
            },
        )

    @patch("chats.apps.api.v1.internal.rest_clients.connect_rest_client.requests.get")
    def test_list_channels_omits_exclude_wpp_demo_when_none(
        self, mock_get, _mock_token
    ):
        mock_get.return_value = MagicMock(status_code=200)

        self.client_rest.list_channels(
            project_uuid=self.project_uuid,
            channel_type="whatsapp",
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertNotIn("exclude_wpp_demo", called_params)

    @patch("chats.apps.api.v1.internal.rest_clients.connect_rest_client.requests.get")
    def test_list_channels_with_additional_query_params(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(status_code=200)

        response = self.client_rest.list_channels(
            project_uuid=self.project_uuid,
            channel_type="whatsapp",
            is_active=True,
            name="my-channel",
        )

        mock_get.assert_called_once_with(
            url=f"{CONNECT_BASE_URL}/v2/projects/channels",
            headers=self.client_rest.headers,
            params={
                "project_uuid": str(self.project_uuid),
                "channel_type": "whatsapp",
                "is_active": True,
                "name": "my-channel",
            },
        )
        self.assertEqual(response.status_code, 200)

    @patch("chats.apps.api.v1.internal.rest_clients.connect_rest_client.requests.get")
    def test_list_channels_omits_none_kwargs(self, mock_get, _mock_token):
        mock_get.return_value = MagicMock(status_code=200)

        self.client_rest.list_channels(
            project_uuid=self.project_uuid,
            channel_type="whatsapp",
            is_active=None,
            name="my-channel",
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertNotIn("is_active", called_params)
        self.assertIn("name", called_params)
