from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionStatus,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


User = get_user_model()


class AudioTranscriptionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="audio@example.com", password="x"
        )
        self.project = Project.objects.create(name="Audio Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.sector = Sector.objects.create(
            name="S",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Q", sector=self.sector)
        self.contact = Contact.objects.create(name="C")
        self.room = Room.objects.create(
            queue=self.queue, user=self.user, contact=self.contact, is_active=True
        )
        self.message = Message.objects.create(
            room=self.room, text="audio", contact=self.contact
        )
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="audio/ogg",
            media_url="http://example.com/a.ogg",
        )
        self.client.force_authenticate(user=self.user)
        self.url = f"/v1/ai_features/transcription/{self.message.uuid}/"

    def test_no_audio_media(self):
        other = Message.objects.create(room=self.room, text="text")
        response = self.client.post(f"/v1/ai_features/transcription/{other.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=False)
    def test_permission_denied(self, _can_retrieve):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_closed_room(self, _can_retrieve):
        self.room.is_active = False
        self.room.save(update_fields=["is_active"])
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(AUDIO_TRANSCRIPTION_MAX_DURATION_SECONDS=10)
    @patch(
        "chats.apps.ai_features.audio_transcription.views.get_audio_duration_seconds",
        return_value=99,
    )
    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_duration_exceeded(self, _can_retrieve, _duration):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.ai_features.audio_transcription.views.transcribe_audio.delay")
    @patch(
        "chats.apps.ai_features.audio_transcription.views.get_audio_duration_seconds",
        return_value=5,
    )
    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_create_transcription(self, _can_retrieve, _duration, mock_delay):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], AudioTranscriptionStatus.QUEUED)
        mock_delay.assert_called_once()
        self.assertTrue(
            AudioTranscription.objects.filter(media=self.media).exists()
        )

    @patch(
        "chats.apps.ai_features.audio_transcription.views.get_audio_duration_seconds",
        return_value=5,
    )
    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_existing_done_transcription(self, _can_retrieve, _duration):
        AudioTranscription.objects.create(
            media=self.media, status=AudioTranscriptionStatus.DONE, text="hi"
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AudioTranscriptionStatus.DONE)

    @patch(
        "chats.apps.ai_features.audio_transcription.views.get_audio_duration_seconds",
        return_value=5,
    )
    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_existing_queued_transcription(self, _can_retrieve, _duration):
        AudioTranscription.objects.create(
            media=self.media, status=AudioTranscriptionStatus.QUEUED
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AudioTranscriptionStatus.QUEUED)

    @patch("chats.apps.ai_features.audio_transcription.views.transcribe_audio.delay")
    @patch(
        "chats.apps.ai_features.audio_transcription.views.get_audio_duration_seconds",
        return_value=5,
    )
    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_retry_failed_transcription(self, _can_retrieve, _duration, mock_delay):
        AudioTranscription.objects.create(
            media=self.media, status=AudioTranscriptionStatus.FAILED
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once()


class AudioTranscriptionFeedbackViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="feedback@example.com", password="x"
        )
        self.project = Project.objects.create(name="Feedback Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.sector = Sector.objects.create(
            name="S",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Q", sector=self.sector)
        self.contact = Contact.objects.create(name="C")
        self.room = Room.objects.create(
            queue=self.queue, user=self.user, contact=self.contact
        )
        self.message = Message.objects.create(
            room=self.room, text="audio", contact=self.contact
        )
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="audio/ogg",
            media_url="http://example.com/a.ogg",
        )
        self.transcription = AudioTranscription.objects.create(
            media=self.media,
            status=AudioTranscriptionStatus.DONE,
            text="hello",
        )
        self.client.force_authenticate(user=self.user)
        self.url = f"/v1/msg/{self.message.uuid}/transcription/feedback/"

    def test_no_audio_media(self):
        other = Message.objects.create(room=self.room, text="text")
        response = self.client.post(
            f"/v1/msg/{other.uuid}/transcription/feedback/",
            {"liked": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=False)
    def test_permission_denied(self, _can_retrieve):
        response = self.client.post(self.url, {"liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_transcription_not_found(self, _can_retrieve):
        self.transcription.delete()
        response = self.client.post(self.url, {"liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_create_feedback(self, _can_retrieve):
        response = self.client.post(self.url, {"liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["liked"])

    @patch("chats.apps.rooms.models.Room.can_retrieve", return_value=True)
    def test_update_feedback(self, _can_retrieve):
        self.client.post(self.url, {"liked": True}, format="json")
        response = self.client.post(self.url, {"liked": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["liked"])


class AudioTranscriptionFeedbackTagsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="tags@example.com", password="x")
        self.client.force_authenticate(user=self.user)

    def test_get_tags(self):
        response = self.client.get("/v1/ai_features/transcription/feedback/tags/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertTrue(len(response.data["results"]) > 0)
