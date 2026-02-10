from django.db import models
from django.utils.translation import gettext_lazy as _


class AudioTranscriptionFeedbackTags(models.TextChoices):
    """
    Text choices with the possible tags of the audio transcription feedback.
    """

    INCORRECT_TRANSCRIPTION = "INCORRECT_TRANSCRIPTION", _("Incorrect transcription")
    INCOMPLETE_TRANSCRIPTION = "INCOMPLETE_TRANSCRIPTION", _("Incomplete transcription")
    HARD_TO_UNDERSTAND = "HARD_TO_UNDERSTAND", _("Hard to understand")
    DID_NOT_LOAD = "DID_NOT_LOAD", _("Did not load")
