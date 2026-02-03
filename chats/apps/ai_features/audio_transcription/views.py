import logging

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.ai_features.audio_transcription.enums import (
    AudioTranscriptionFeedbackTags,
)
from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionStatus,
)
from chats.apps.ai_features.audio_transcription.serializers import (
    AudioTranscriptionCreateResponseSerializer,
    AudioTranscriptionFeedbackCreateSerializer,
)
from chats.apps.ai_features.audio_transcription.tasks import transcribe_audio
from chats.apps.ai_features.audio_transcription.utils import get_audio_duration_seconds
from chats.apps.msgs.models import MessageMedia
from chats.core.mixins import LanguageViewMixin

logger = logging.getLogger(__name__)


class AudioTranscriptionView(APIView):
    """
    API view to create an audio transcription for a message.
    """

    permission_classes = [IsAuthenticated]

    def get_audio_media(self, msg_uuid: str) -> MessageMedia:
        """
        Get the first audio media from a message by message UUID.
        Queries MessageMedia table directly (more efficient than querying Message).
        """
        return MessageMedia.objects.select_related(
            "message__room"
        ).filter(
            message_id=msg_uuid,
            content_type__startswith="audio",
        ).first()

    def post(self, request, msg_uuid: str):
        """
        Create an audio transcription for a message.
        Expects the message to have audio media attached.
        """
        # Get the first audio media from the message (queries MessageMedia table)
        audio_media = self.get_audio_media(msg_uuid)

        if not audio_media:
            return Response(
                {"detail": _("No audio media found in this message.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if room is closed (history)
        if not audio_media.message.room.is_active:
            return Response(
                {"detail": _("Cannot transcribe audio from closed rooms.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check audio duration
        max_duration = settings.AUDIO_TRANSCRIPTION_MAX_DURATION_SECONDS
        audio_duration = get_audio_duration_seconds(audio_media)

        if audio_duration is not None and audio_duration > max_duration:
            return Response(
                {
                    "detail": _(
                        "Audio duration exceeds the maximum allowed "
                        "(%(max)s seconds). Audio duration: %(duration)s seconds."
                    ) % {"max": max_duration, "duration": int(audio_duration)}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if transcription already exists
        existing_transcription = AudioTranscription.objects.filter(
            media=audio_media
        ).first()

        if existing_transcription:
            # If already done, return the existing one
            if existing_transcription.status == AudioTranscriptionStatus.DONE:
                return Response(
                    {"status": existing_transcription.status},
                    status=status.HTTP_200_OK,
                )
            # If still processing or queued, return current status
            if existing_transcription.status in [
                AudioTranscriptionStatus.QUEUED,
                AudioTranscriptionStatus.PROCESSING,
            ]:
                return Response(
                    {"status": existing_transcription.status},
                    status=status.HTTP_200_OK,
                )
            # If failed, allow retry by creating a new one
            existing_transcription.delete()

        # Create new transcription
        transcription = AudioTranscription.objects.create(
            media=audio_media,
            status=AudioTranscriptionStatus.QUEUED,
        )

        # Dispatch Celery task
        transcribe_audio.delay(str(transcription.uuid))

        serializer = AudioTranscriptionCreateResponseSerializer(
            {"status": AudioTranscriptionStatus.QUEUED}
        )
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class AudioTranscriptionFeedbackView(APIView):
    """
    API view to create feedback for an audio transcription.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, msg_uuid: str):
        """
        Create feedback for an audio transcription.
        """
        # Get audio media directly from MessageMedia table
        audio_media = MessageMedia.objects.filter(
            message_id=msg_uuid,
            content_type__startswith="audio",
        ).first()

        if not audio_media:
            return Response(
                {"detail": _("No audio media found in this message.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            transcription = AudioTranscription.objects.get(media=audio_media)
        except AudioTranscription.DoesNotExist:
            return Response(
                {"detail": _("Transcription not found for this message.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AudioTranscriptionFeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update or create feedback
        feedback, created = transcription.feedbacks.update_or_create(
            user=request.user,
            defaults=serializer.validated_data,
        )

        return Response(
            {"liked": feedback.liked},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AudioTranscriptionFeedbackTagsView(LanguageViewMixin, APIView):
    """
    API view to get the possible tags for the audio transcription feedback.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get the possible tags for the audio transcription feedback.
        """
        language = self.get_language()

        translation.activate(language)
        results = {}

        for choice in AudioTranscriptionFeedbackTags:
            results[choice.value] = str(choice.label)

        return Response({"results": results}, status=status.HTTP_200_OK)
