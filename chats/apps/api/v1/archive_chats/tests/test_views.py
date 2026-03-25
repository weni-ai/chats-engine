from unittest.mock import patch
from unittest.mock import MagicMock
import uuid

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.response import Response
from django.urls import reverse


class BaseTestGetArchivedMediaView(APITestCase):
    def get_archived_media(self, params: dict) -> Response:
        url = reverse("get_archived_media")

        return self.client.get(url, params)


class TestGetArchivedMediaView(BaseTestGetArchivedMediaView):
    @patch("chats.apps.api.v1.archive_chats.views.GetArchivedMediaView.service")
    def test_get_archived_media_with_valid_params(self, mock_service):
        valid_uuid = uuid.uuid4()
        mock_get_archived_media_url = MagicMock()
        url = f"https://test-bucket.s3.amazonaws.com/archived_conversations/{valid_uuid}/{valid_uuid}/media/test.jpg"
        mock_get_archived_media_url.return_value = url
        mock_service.get_archived_media_url = mock_get_archived_media_url
        params = {
            "object_key": f"archived_conversations/{valid_uuid}/{valid_uuid}/media/test.jpg",
        }

        response = self.get_archived_media(params)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            response.url,
            f"https://test-bucket.s3.amazonaws.com/archived_conversations/{valid_uuid}/{valid_uuid}/media/test.jpg",
        )
