import uuid
from unittest.mock import patch

from django.test import TestCase

from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionStatus,
)
from chats.apps.ai_features.audio_transcription.tasks import (
    cancel_audio_transcription,
    transcribe_audio,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class _BaseAudioTranscriptionTaskTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="AT Test Project")
        self.sector = Sector.objects.create(
            name="AT Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="AT Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="AT Contact")
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.message = Message.objects.create(
            room=self.room, text="audio", contact=self.contact
        )
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="audio/ogg",
            media_url="http://example.com/audio.ogg",
        )
        self.transcription = AudioTranscription.objects.create(media=self.media)


class TestTranscribeAudio(_BaseAudioTranscriptionTaskTestCase):
    @patch(
        "chats.apps.ai_features.audio_transcription.tasks.AudioTranscriptionService"
    )
    def test_calls_service_when_transcription_exists(self, mock_service_class):
        transcribe_audio(self.transcription.uuid)

        mock_service_class.assert_called_once_with()
        mock_service_class.return_value.transcribe.assert_called_once_with(
            self.transcription
        )

    @patch(
        "chats.apps.ai_features.audio_transcription.tasks.AudioTranscriptionService"
    )
    def test_returns_silently_when_transcription_does_not_exist(
        self, mock_service_class
    ):
        result = transcribe_audio(uuid.uuid4())

        self.assertIsNone(result)
        mock_service_class.assert_not_called()


class TestCancelAudioTranscription(_BaseAudioTranscriptionTaskTestCase):
    @patch.object(AudioTranscription, "notify_transcription")
    def test_cancels_queued_transcription(self, mock_notify):
        cancel_audio_transcription(self.transcription.uuid)

        self.transcription.refresh_from_db()
        self.assertEqual(
            self.transcription.status, AudioTranscriptionStatus.FAILED
        )
        mock_notify.assert_called_once()

    @patch.object(AudioTranscription, "notify_transcription")
    def test_does_not_change_non_queued_transcription(self, mock_notify):
        self.transcription.status = AudioTranscriptionStatus.DONE
        self.transcription.save(update_fields=["status"])

        cancel_audio_transcription(self.transcription.uuid)

        self.transcription.refresh_from_db()
        self.assertEqual(self.transcription.status, AudioTranscriptionStatus.DONE)
        mock_notify.assert_not_called()

    @patch.object(AudioTranscription, "notify_transcription")
    def test_returns_silently_when_transcription_does_not_exist(self, mock_notify):
        result = cancel_audio_transcription(uuid.uuid4())

        self.assertIsNone(result)
        mock_notify.assert_not_called()
