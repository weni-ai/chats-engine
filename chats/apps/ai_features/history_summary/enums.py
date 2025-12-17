from django.db import models
from django.utils.translation import gettext_lazy as _


class HistorySummaryFeedbackTags(models.TextChoices):
    """
    Text choices with the possible tags of the history summary feedback.
    """

    INCORRECT_SUMMARY = "INCORRECT_SUMMARY", _("Incorrect summary")
    INCOMPLETE_SUMMARY = "INCOMPLETE_SUMMARY", _("Incomplete summary")
    CONFUSING_SUMMARY = "CONFUSING_SUMMARY", _("Confusing summary")
    HAD_TO_READ_FULL_CONVERSATION = "HAD_TO_READ_FULL_CONVERSATION", _(
        "I had to read the full conversation"
    )
    DID_NOT_SPEED_UP_WORKFLOW = "DID_NOT_SPEED_UP_WORKFLOW", _(
        "Did not speed up the workflow"
    )
    HARD_TO_UNDERSTAND_LANGUAGE = "HARD_TO_UNDERSTAND_LANGUAGE", _(
        "Hard to understand language"
    )
    DID_NOT_LOAD = "DID_NOT_LOAD", _("Did not load")
    UNCLEAR_INTERFACE = "UNCLEAR_INTERFACE", _("Unclear interface")
