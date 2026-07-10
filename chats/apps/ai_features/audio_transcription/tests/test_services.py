import io
import json
from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionStatus,
)
from chats.apps.ai_features.audio_transcription.services import (
    AudioTranscriptionService,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class AudioTranscriptionServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="AT Service Project")
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

    def _lambda_response(self, body_text=None, error=None, error_message=None):
        if error or error_message:
            payload = {}
            if error:
                payload["error"] = error
            if error_message:
                payload["errorMessage"] = error_message
        else:
            payload = {
                "response": {
                    "functionResponse": {
                        "responseBody": {"TEXT": {"body": body_text or ""}}
                    }
                }
            }
        mock_response = {"Payload": io.BytesIO(json.dumps(payload).encode("utf-8"))}
        return mock_response

    @patch("chats.apps.ai_features.audio_transcription.services.boto3.client")
    @patch.object(AudioTranscription, "notify_transcription")
    def test_transcribe_success(self, mock_notify, mock_boto):
        client = Mock()
        client.invoke.return_value = self._lambda_response("Hello world")
        mock_boto.return_value = client

        service = AudioTranscriptionService()
        result = service.transcribe(self.transcription)

        self.transcription.refresh_from_db()
        self.assertEqual(result.status, AudioTranscriptionStatus.DONE)
        self.assertEqual(self.transcription.text, "Hello world")
        mock_notify.assert_called_once()

    @patch("chats.apps.ai_features.audio_transcription.services.capture_message")
    @patch("chats.apps.ai_features.audio_transcription.services.boto3.client")
    @patch.object(AudioTranscription, "notify_transcription")
    def test_transcribe_lambda_error_message(self, mock_notify, mock_boto, _capture):
        client = Mock()
        client.invoke.return_value = self._lambda_response(error_message="boom")
        mock_boto.return_value = client

        service = AudioTranscriptionService()
        result = service.transcribe(self.transcription)

        self.transcription.refresh_from_db()
        self.assertEqual(result.status, AudioTranscriptionStatus.FAILED)
        mock_notify.assert_called_once()

    @patch("chats.apps.ai_features.audio_transcription.services.capture_message")
    @patch("chats.apps.ai_features.audio_transcription.services.boto3.client")
    @patch.object(AudioTranscription, "notify_transcription")
    def test_transcribe_text_starts_with_error(self, mock_notify, mock_boto, _capture):
        client = Mock()
        client.invoke.return_value = self._lambda_response("Error: bad audio")
        mock_boto.return_value = client

        service = AudioTranscriptionService()
        result = service.transcribe(self.transcription)

        self.transcription.refresh_from_db()
        self.assertEqual(result.status, AudioTranscriptionStatus.FAILED)
        mock_notify.assert_called_once()

    @patch("chats.apps.ai_features.audio_transcription.services.boto3.client")
    @patch.object(AudioTranscription, "notify_transcription")
    def test_transcribe_empty_text(self, mock_notify, mock_boto):
        client = Mock()
        client.invoke.return_value = self._lambda_response("")
        mock_boto.return_value = client

        service = AudioTranscriptionService()
        result = service.transcribe(self.transcription)

        self.transcription.refresh_from_db()
        self.assertEqual(result.status, AudioTranscriptionStatus.FAILED)
        mock_notify.assert_called_once()

    @patch("chats.apps.ai_features.audio_transcription.services.capture_exception")
    @patch("chats.apps.ai_features.audio_transcription.services.boto3.client")
    @patch.object(AudioTranscription, "notify_transcription")
    def test_transcribe_exception(self, mock_notify, mock_boto, mock_capture):
        client = Mock()
        client.invoke.side_effect = RuntimeError("network")
        mock_boto.return_value = client

        service = AudioTranscriptionService()
        result = service.transcribe(self.transcription)

        self.transcription.refresh_from_db()
        self.assertEqual(result.status, AudioTranscriptionStatus.FAILED)
        mock_capture.assert_called_once()
        mock_notify.assert_called_once()

    @patch("chats.apps.ai_features.audio_transcription.services.boto3.client")
    def test_build_payload(self, mock_boto):
        mock_boto.return_value = Mock()
        service = AudioTranscriptionService()
        payload = service._build_payload(self.media)
        self.assertEqual(payload["function"], "transcribe_audio")
        self.assertEqual(payload["parameters"][0]["name"], "audio_url")
