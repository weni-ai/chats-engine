from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import MessageMedia
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class TestMessageMediaViewSetV2(APITestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            email="agent@test.com",
            password="testpass123",
            first_name="João",
            last_name="Silva",
        )
        self.other_agent = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            name="Maria Cliente", email="cliente@test.com"
        )
        self.room = Room.objects.create(
            contact=self.contact,
            is_active=True,
            queue=self.queue,
            user=self.agent,
        )
        self.client.force_authenticate(user=self.agent)

    def _create_test_image(self):
        file_content = BytesIO()
        file_content.write(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        file_content.seek(0)
        return SimpleUploadedFile(
            "test_image.png", file_content.read(), content_type="image/png"
        )

    @patch(
        "chats.apps.api.v1.msgs.serializers.magic.from_buffer", return_value="image/png"
    )
    def test_create_media_for_room_without_message(self, mock_magic):
        url = reverse("media-v2-list")
        data = {
            "room": str(self.room.uuid),
            "content_type": "image/jpeg",
            "media_file": self._create_test_image(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("uuid", response.data)
        media = MessageMedia.objects.get(uuid=response.data["uuid"])
        self.assertIsNone(media.message_id)
        self.assertEqual(media.room_id, self.room.uuid)
        self.assertEqual(media.content_type, "image/png")

    def test_create_media_forbidden_for_other_agent(self):
        self.client.force_authenticate(user=self.other_agent)
        url = reverse("media-v2-list")
        data = {
            "room": str(self.room.uuid),
            "media_file": self._create_test_image(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        "chats.apps.api.v1.msgs.serializers.magic.from_buffer", return_value="image/png"
    )
    def test_create_media_rejects_closed_room(self, mock_magic):
        self.room.is_active = False
        self.room.save(update_fields=["is_active"])
        url = reverse("media-v2-list")
        data = {
            "room": str(self.room.uuid),
            "media_file": self._create_test_image(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
