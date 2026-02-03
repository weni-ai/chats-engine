from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestMessageViewsetCreateMedia(APITestCase):
    """Tests for the create_media endpoint to ensure last_message is updated correctly."""

    def setUp(self):
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
            name="Test Contact", email="contact@test.com"
        )
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        self.user = User.objects.create_user(
            email="agent@test.com", password="testpass123"
        )
        self.room.user = self.user
        self.room.save(update_fields=["user"])

        self.client.force_authenticate(user=self.user)

    def _create_test_image(self):
        """Create a simple test image file."""
        file_content = BytesIO()
        # Simple 1x1 pixel PNG
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

    def _create_test_audio(self):
        """Create a simple test audio file."""
        return SimpleUploadedFile(
            "test_audio.mp3", b"fake audio content", content_type="audio/mpeg"
        )

    @patch("chats.apps.msgs.models.MessageMedia.callback")
    def test_create_media_updates_last_message_with_image(self, mock_callback):
        """Test that creating a message with image updates room's last_message."""
        self.assertIsNone(self.room.last_message)

        url = reverse("message-create_media")
        data = {
            "message.room": str(self.room.uuid),
            "message.user_email": self.user.email,
            "message.text": "",
            "content_type": "image/png",
            "media_file": self._create_test_image(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.room.refresh_from_db()
        self.assertIsNotNone(self.room.last_message)
        self.assertEqual(self.room.last_message_user, self.user)
        self.assertEqual(len(self.room.last_message_media), 1)
        self.assertEqual(self.room.last_message_media[0]["content_type"], "image/png")

    @patch("chats.apps.msgs.models.MessageMedia.callback")
    def test_create_media_updates_last_message_with_audio(self, mock_callback):
        """Test that creating a message with audio updates room's last_message."""
        self.assertIsNone(self.room.last_message)

        url = reverse("message-create_media")
        data = {
            "message.room": str(self.room.uuid),
            "message.user_email": self.user.email,
            "message.text": "",
            "content_type": "audio/mpeg",
            "media_file": self._create_test_audio(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.room.refresh_from_db()
        self.assertIsNotNone(self.room.last_message)
        self.assertEqual(self.room.last_message_user, self.user)
        self.assertEqual(len(self.room.last_message_media), 1)
        self.assertEqual(self.room.last_message_media[0]["content_type"], "audio/mpeg")

    @patch("chats.apps.msgs.models.MessageMedia.callback")
    def test_create_media_without_text_updates_last_message(self, mock_callback):
        """
        Test that creating a message with ONLY media (no text) still updates last_message.
        This is the specific bug fix scenario - before the fix, messages with only media
        and no text would not update last_message due to ORM cache issues.
        """
        self.assertIsNone(self.room.last_message)
        self.assertEqual(self.room.last_message_text, "")

        url = reverse("message-create_media")
        data = {
            "message.room": str(self.room.uuid),
            "message.user_email": self.user.email,
            "message.text": "",  # No text, only media
            "content_type": "image/png",
            "media_file": self._create_test_image(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.room.refresh_from_db()
        # The key assertion - last_message should be set even without text
        self.assertIsNotNone(self.room.last_message)
        self.assertIsNotNone(self.room.last_interaction)

    @patch("chats.apps.msgs.models.MessageMedia.callback")
    def test_create_media_with_text_updates_last_message_text(self, mock_callback):
        """Test that creating a message with media AND text updates both fields."""
        url = reverse("message-create_media")
        data = {
            "message.room": str(self.room.uuid),
            "message.user_email": self.user.email,
            "message.text": "Check this image",
            "content_type": "image/png",
            "media_file": self._create_test_image(),
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.room.refresh_from_db()
        self.assertIsNotNone(self.room.last_message)
        self.assertEqual(self.room.last_message_text, "Check this image")
        self.assertEqual(len(self.room.last_message_media), 1)


class TestMessageViewsetCreate(APITestCase):
    """Tests for regular message creation."""

    def setUp(self):
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
            name="Test Contact", email="contact@test.com"
        )
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        self.user = User.objects.create_user(
            email="agent@test.com", password="testpass123"
        )
        self.room.user = self.user
        self.room.save(update_fields=["user"])

        self.client.force_authenticate(user=self.user)

    def test_create_text_message_updates_last_message(self):
        """Test that creating a text message updates room's last_message."""
        self.assertIsNone(self.room.last_message)

        url = reverse("message-list")
        data = {
            "room": str(self.room.uuid),
            "user_email": self.user.email,
            "text": "Hello from agent",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.room.refresh_from_db()
        self.assertIsNotNone(self.room.last_message)
        self.assertEqual(self.room.last_message_text, "Hello from agent")
        self.assertEqual(self.room.last_message_user, self.user)
