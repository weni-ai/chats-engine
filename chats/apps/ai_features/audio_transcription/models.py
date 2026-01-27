from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.apps.accounts.models import User
from chats.apps.msgs.models import MessageMedia
from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group


class AudioTranscriptionStatus(models.TextChoices):
    """
    A model to store the status of the audio transcription.
    """

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class AudioTranscription(BaseModel):
    """
    A model to store the audio transcription of a message media.
    """

    media = models.OneToOneField(
        MessageMedia,
        on_delete=models.CASCADE,
        related_name="transcription",
    )
    status = models.CharField(
        max_length=12,
        choices=AudioTranscriptionStatus.choices,
        default=AudioTranscriptionStatus.QUEUED,
    )
    text = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = _("Audio Transcription")
        verbose_name_plural = _("Audio Transcriptions")

    def __str__(self):
        return f"{self.media.pk} - {self.status}"

    def update_status(self, status: AudioTranscriptionStatus):
        self.status = status
        self.save(update_fields=["status"])

    @property
    def room(self):
        return self.media.message.room

    @property
    def ws_group_name(self) -> str:
        return f"room_{self.room.pk}"

    @property
    def serialized_ws_data(self) -> dict:
        return {
            "message_uuid": str(self.media.message.uuid),
            "text": self.text or "",
            "status": self.status,
        }

    def notify_transcription(self):
        """
        Notify the room about the transcription status via WebSocket.
        """
        send_channels_group(
            group_name=self.ws_group_name,
            call_type="notify",
            content=self.serialized_ws_data,
            action="media.transcribe",
        )


class AudioTranscriptionFeedback(BaseModel):
    """
    A model to store the user feedback of the audio transcription.
    """

    transcription = models.ForeignKey(
        AudioTranscription,
        verbose_name=_("Audio Transcription"),
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    user = models.ForeignKey(
        User,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
        related_name="audio_transcription_feedbacks",
    )
    liked = models.BooleanField(_("Liked?"))
    text = models.CharField(_("Text"), max_length=150, blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)

    class Meta:
        verbose_name = _("Audio Transcription Feedback")
        verbose_name_plural = _("Audio Transcription Feedbacks")
        constraints = [
            models.UniqueConstraint(
                fields=["transcription", "user"],
                name="unique_audio_transcription_user_feedback",
            )
        ]

    def __str__(self):
        return f"{self.transcription.pk} - {self.user.email}"
