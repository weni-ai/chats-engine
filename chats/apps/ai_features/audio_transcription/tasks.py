import logging
from uuid import UUID

from chats.celery import app
from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionStatus,
)
from chats.apps.ai_features.audio_transcription.services import (
    AudioTranscriptionService,
)

logger = logging.getLogger(__name__)


@app.task
def transcribe_audio(transcription_uuid: UUID):
    """
    Transcribe audio from a message media.
    """
    try:
        transcription = AudioTranscription.objects.get(uuid=transcription_uuid)
    except AudioTranscription.DoesNotExist:
        logger.error(
            "AudioTranscription with uuid %s does not exist",
            transcription_uuid,
        )
        return

    service = AudioTranscriptionService()
    service.transcribe(transcription)


@app.task
def cancel_audio_transcription(transcription_uuid: UUID):
    """
    Cancel an audio transcription if it's still queued after some time.
    """
    try:
        transcription = AudioTranscription.objects.get(uuid=transcription_uuid)
    except AudioTranscription.DoesNotExist:
        logger.error(
            "AudioTranscription with uuid %s does not exist",
            transcription_uuid,
        )
        return

    if transcription.status == AudioTranscriptionStatus.QUEUED:
        transcription.status = AudioTranscriptionStatus.FAILED
        transcription.save(update_fields=["status"])
        transcription.notify_transcription()
        logger.warning(
            "AudioTranscription %s was cancelled due to timeout",
            transcription_uuid,
        )
