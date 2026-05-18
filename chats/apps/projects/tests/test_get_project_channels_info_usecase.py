import uuid

from unittest.mock import Mock

from django.test import TestCase

from chats.apps.projects.usecases.get_project_channels_info import (
    GetProjectChannelsInfoUseCase,
)


class TestGetProjectChannelsInfoUseCase(TestCase):
    def setUp(self):
        self.project_uuid = str(uuid.uuid4())
        self.use_case = GetProjectChannelsInfoUseCase(
            project_uuid=self.project_uuid
        )
        self.mock_connect_client = Mock()
        self.use_case.connect_client = self.mock_connect_client

    def test_returns_channels_list(self):
        channels = [
            {
                "uuid": str(uuid.uuid4()),
                "name": "Channel 1",
                "config": {"wa_waba_id": "111"},
                "address": "+5511999999999",
                "is_active": True,
            },
            {
                "uuid": str(uuid.uuid4()),
                "name": "Channel 2",
                "config": {"wa_waba_id": "222"},
                "address": "+5511888888888",
                "is_active": True,
            },
        ]
        mock_response = Mock()
        mock_response.json.return_value = {"channels": channels}
        self.mock_connect_client.list_channels.return_value = mock_response

        result = self.use_case.execute()

        self.assertEqual(result, channels)
        self.assertEqual(len(result), 2)

    def test_empty_channels_returns_empty_list(self):
        mock_response = Mock()
        mock_response.json.return_value = {"channels": []}
        self.mock_connect_client.list_channels.return_value = mock_response

        result = self.use_case.execute()

        self.assertEqual(result, [])

    def test_calls_connect_with_correct_params(self):
        mock_response = Mock()
        mock_response.json.return_value = {"channels": []}
        self.mock_connect_client.list_channels.return_value = mock_response

        self.use_case.execute()

        self.mock_connect_client.list_channels.assert_called_once_with(
            project_uuid=self.project_uuid,
            channel_type="WAC",
            exclude_wpp_demo=True,
        )
