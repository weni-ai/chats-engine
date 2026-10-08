from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response


from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.contacts.models import Contact
from chats.apps.accounts.models import User
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.msgs.models import Message, MessageMedia


class BaseTestMessageMediaViewSet(APITestCase):
    def list_media(self, params: dict) -> Response:
        url = reverse("media-list")

        return self.client.get(url, params)

    def download_media(self, media_uuid) -> Response:
        url = reverse("media-download", kwargs={"uuid": media_uuid})

        return self.client.get(url)

    def download_message(self, message_uuid) -> Response:
        url = reverse("message-download", kwargs={"uuid": message_uuid})

        return self.client.get(url)


class TestMessageMediaViewSetAsAnonymousUser(BaseTestMessageMediaViewSet):
    def test_list_media_as_anonymous_user(self):
        response = self.list_media({})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestMessageMediaViewSetAsAuthenticatedUser(BaseTestMessageMediaViewSet):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            work_start="09:00",
            work_end="18:00",
            rooms_limit=10,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact", email="test@test.com"),
            is_active=True,
            queue=self.queue,
        )
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

        self.client.force_authenticate(user=self.user)

    def test_list_media_without_permission(self):
        response = self.list_media({"room": self.room.uuid})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_when_user_is_room_user(self):
        self.room.user = self.user
        self.room.save(update_fields=["user"])

        response = self.list_media({"room": self.room.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission()
    def test_list_when_user_with_without_room_and_project_query_param(
        self,
    ):
        response = self.list_media({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"][0].code, "required")

    @with_project_permission()
    def test_list_when_user_with_project_permission_and_project_query_param(self):
        response = self.list_media({"project": self.project.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission()
    def test_list_when_user_with_project_permission_and_room_query_param(self):
        message = Message.objects.create(room=self.room, user=self.user)
        MessageMedia.objects.create(message=message)
        response = self.list_media({"room": self.room.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission()
    def test_list_when_user_filtering_by_room_and_contact(self):
        message = Message.objects.create(room=self.room, user=self.user)
        MessageMedia.objects.create(message=message)
        response = self.list_media(
            {"room": self.room.uuid, "contact": self.room.contact.uuid}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["message"], message.uuid)


class TestMessageMediaViewSetDownload(BaseTestMessageMediaViewSet):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            work_start="09:00",
            work_end="18:00",
            rooms_limit=10,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=Contact.objects.create(
                name="Test Contact", email="download-contact@test.com"
            ),
            is_active=True,
            queue=self.queue,
        )
        self.agent = User.objects.create_user(
            email="download-agent@test.com", password="testpass123"
        )
        self.room.user = self.agent
        self.room.save(update_fields=["user"])

        self.user = User.objects.create_user(
            email="download-user@test.com", password="testpass123"
        )

        self.message = Message.objects.create(room=self.room, user=self.agent)
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="audio/mpeg",
            media_file=SimpleUploadedFile(
                "audio.mp3", b"fake audio content", content_type="audio/mpeg"
            ),
        )

    def test_download_media_as_anonymous_user(self):
        response = self.download_media(self.media.uuid)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_media_as_room_agent(self):
        self.client.force_authenticate(user=self.agent)

        response = self.download_media(self.media.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response.getvalue(), b"fake audio content")

    def test_download_media_as_unrelated_user_without_permission(self):
        self.client.force_authenticate(user=self.user)

        response = self.download_media(self.media.uuid)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission()
    def test_download_media_as_project_member(self):
        self.client.force_authenticate(user=self.user)

        response = self.download_media(self.media.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue(), b"fake audio content")

    def test_download_media_not_found(self):
        self.client.force_authenticate(user=self.agent)

        response = self.download_media("11111111-1111-1111-1111-111111111111")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "chats.apps.msgs.models.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_download_media_with_media_url(self, _mock_ff):
        media = MessageMedia.objects.create(
            message=self.message,
            content_type="image/png",
            media_url="https://example.com/files/image.png",
        )
        self.client.force_authenticate(user=self.agent)

        mock_upstream = Mock()
        mock_upstream.raise_for_status = Mock()
        mock_upstream.headers = {"Content-Type": "image/png"}
        mock_upstream.iter_content = Mock(return_value=iter([b"external-bytes"]))

        with patch(
            "chats.apps.api.v1.msgs.media_download.get_request_session_with_retries"
        ) as mock_session:
            mock_session.return_value.get.return_value = mock_upstream
            response = self.download_media(media.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response.getvalue(), b"external-bytes")

    @patch(
        "chats.apps.msgs.models.is_feature_active_for_attributes",
        return_value=True,
    )
    def test_download_media_uses_flows_proxy_url_when_feature_active(self, _mock_ff):
        """
        When the Flows media url feature flag is active, the backend must
        fetch the Flows proxy URL (server-side), following its redirect to
        the presigned S3 URL itself, instead of relying on the browser to
        do it directly (which is what caused CORS failures).
        """
        media = MessageMedia.objects.create(
            message=self.message,
            content_type="audio/mpeg",
            media_url="https://push-media.example.com/media/audio.mp3",
        )
        expected_flows_url = media.get_flows_media_url(media.url)
        self.client.force_authenticate(user=self.agent)

        mock_upstream = Mock()
        mock_upstream.raise_for_status = Mock()
        mock_upstream.headers = {"Content-Type": "audio/mpeg"}
        mock_upstream.iter_content = Mock(return_value=iter([b"flows-proxied-bytes"]))

        with patch(
            "chats.apps.api.v1.msgs.media_download.get_request_session_with_retries"
        ) as mock_session:
            mock_session.return_value.get.return_value = mock_upstream
            response = self.download_media(media.uuid)

        mock_session.return_value.get.assert_called_once_with(
            expected_flows_url, stream=True, timeout=30, allow_redirects=True
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue(), b"flows-proxied-bytes")

    @patch(
        "chats.apps.msgs.models.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_download_media_upstream_failure(self, _mock_ff):
        media = MessageMedia.objects.create(
            message=self.message,
            content_type="image/png",
            media_url="https://example.com/files/image.png",
        )
        self.client.force_authenticate(user=self.agent)

        with patch(
            "chats.apps.api.v1.msgs.media_download.get_request_session_with_retries"
        ) as mock_session:
            mock_session.return_value.get.side_effect = ConnectionError("boom")
            response = self.download_media(media.uuid)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)


class TestMessageViewSetDownload(BaseTestMessageMediaViewSet):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            work_start="09:00",
            work_end="18:00",
            rooms_limit=10,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=Contact.objects.create(
                name="Test Contact", email="msg-download-contact@test.com"
            ),
            is_active=True,
            queue=self.queue,
        )
        self.agent = User.objects.create_user(
            email="msg-download-agent@test.com", password="testpass123"
        )
        self.room.user = self.agent
        self.room.save(update_fields=["user"])

        self.user = User.objects.create_user(
            email="msg-download-user@test.com", password="testpass123"
        )

        self.message = Message.objects.create(room=self.room, user=self.agent)
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="audio/mpeg",
            media_file=SimpleUploadedFile(
                "audio.mp3", b"fake audio content", content_type="audio/mpeg"
            ),
        )

    def test_download_message_as_anonymous_user(self):
        response = self.download_message(self.message.uuid)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_message_as_room_agent(self):
        self.client.force_authenticate(user=self.agent)

        response = self.download_message(self.message.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response.getvalue(), b"fake audio content")

    def test_download_message_as_unrelated_user_without_permission(self):
        self.client.force_authenticate(user=self.user)

        response = self.download_message(self.message.uuid)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission()
    def test_download_message_as_project_member(self):
        self.client.force_authenticate(user=self.user)

        response = self.download_message(self.message.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue(), b"fake audio content")

    def test_download_message_not_found(self):
        self.client.force_authenticate(user=self.agent)

        response = self.download_message("11111111-1111-1111-1111-111111111111")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_message_without_audio_media(self):
        message = Message.objects.create(room=self.room, user=self.agent)
        MessageMedia.objects.create(
            message=message,
            content_type="image/png",
            media_url="https://example.com/files/image.png",
        )
        self.client.force_authenticate(user=self.agent)

        response = self.download_message(message.uuid)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "chats.apps.msgs.models.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_download_message_with_media_url(self, _mock_ff):
        message = Message.objects.create(room=self.room, user=self.agent)
        MessageMedia.objects.create(
            message=message,
            content_type="audio/mpeg",
            media_url="https://example.com/files/audio.mp3",
        )
        self.client.force_authenticate(user=self.agent)

        mock_upstream = Mock()
        mock_upstream.raise_for_status = Mock()
        mock_upstream.headers = {"Content-Type": "audio/mpeg"}
        mock_upstream.iter_content = Mock(return_value=iter([b"external-bytes"]))

        with patch(
            "chats.apps.api.v1.msgs.media_download.get_request_session_with_retries"
        ) as mock_session:
            mock_session.return_value.get.return_value = mock_upstream
            response = self.download_message(message.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response.getvalue(), b"external-bytes")

    @patch(
        "chats.apps.msgs.models.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_download_message_upstream_failure(self, _mock_ff):
        message = Message.objects.create(room=self.room, user=self.agent)
        MessageMedia.objects.create(
            message=message,
            content_type="audio/mpeg",
            media_url="https://example.com/files/audio.mp3",
        )
        self.client.force_authenticate(user=self.agent)

        with patch(
            "chats.apps.api.v1.msgs.media_download.get_request_session_with_retries"
        ) as mock_session:
            mock_session.return_value.get.side_effect = ConnectionError("boom")
            response = self.download_message(message.uuid)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
