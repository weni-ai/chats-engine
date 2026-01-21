import json
import logging
from typing import TYPE_CHECKING

import boto3
from django.conf import settings
from sentry_sdk import capture_exception, capture_message

from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionStatus,
)

if TYPE_CHECKING:
    from chats.apps.msgs.models import MessageMedia

logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """
    Service to transcribe audio from a message media using AWS Lambda.
    """

    def __init__(self):
        self.lambda_client = boto3.client(
            "lambda",
            region_name=getattr(settings, "AWS_TRANSCRIPTION_REGION", "us-east-1"),
        )
        self.function_arn = getattr(settings, "AWS_TRANSCRIPTION_LAMBDA_ARN", "")

    def _build_payload(self, media: "MessageMedia") -> dict:
        """
        Build the payload for the Lambda function.
        """
        return {
            "parameters": {
                "media_url": media.url,
                "media_uuid": str(media.uuid),
            },
            "sessionAttributes": {},
            "promptSessionAttributes": {
                "alwaysFormat": "<example>{'msg': {'text': 'Hello, how can I help you today?'}}</example>"
            },
            "agent": {
                "name": "INLINE_AGENT",
                "version": "INLINE_AGENT",
                "id": "INLINE_AGENT",
            },
            "actionGroup": "voice_transcription_function",
            "function": self.function_arn,
            "messageVersion": "1.0",
        }

    def _invoke_lambda(self, payload: dict) -> dict:
        """
        Invoke the Lambda function and return the response.
        """
        response = self.lambda_client.invoke(
            FunctionName=self.function_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        response_payload = json.loads(response["Payload"].read().decode("utf-8"))
        return response_payload

    def transcribe(self, transcription: AudioTranscription) -> AudioTranscription:
        """
        Transcribe audio from a message media.
        """
        media = transcription.media

        transcription.update_status(AudioTranscriptionStatus.PROCESSING)

        try:
            payload = self._build_payload(media)
            response = self._invoke_lambda(payload)

            if response.get("errorMessage") or response.get("error"):
                error_msg = response.get("errorMessage") or response.get("error")
                logger.error(
                    "Error transcribing audio for media %s: %s",
                    media.uuid,
                    error_msg,
                )
                capture_message(
                    f"Error transcribing audio for media {media.uuid}: {error_msg}",
                    level="error",
                )
                transcription.update_status(AudioTranscriptionStatus.FAILED)
                transcription.notify_transcription()
                return transcription

            transcription_text = response.get("text", "")

            if not transcription_text:
                logger.warning(
                    "Empty transcription received for media %s",
                    media.uuid,
                )
                transcription.update_status(AudioTranscriptionStatus.FAILED)
                transcription.notify_transcription()
                return transcription

            transcription.text = transcription_text
            transcription.status = AudioTranscriptionStatus.DONE
            transcription.save(update_fields=["text", "status"])

            logger.info(
                "Successfully transcribed audio for media %s",
                media.uuid,
            )

            transcription.notify_transcription()

        except Exception as e:
            logger.error(
                "Error transcribing audio for media %s: %s",
                media.uuid,
                str(e),
            )
            capture_exception(e)
            transcription.update_status(AudioTranscriptionStatus.FAILED)
            transcription.notify_transcription()

        return transcription
