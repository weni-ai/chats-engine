from django.db import models
from django.utils.translation import gettext_lazy as _


class ImprovedUserMessageStatusChoices(models.TextChoices):
    """
    A model to store the status of the improved user message.
    """

    USED = "USED", _("Used")
    DISCARDED = "DISCARDED", _("Discarded")
    EDITED = "EDITED", _("Edited")


class ImprovedUserMessageTypeChoices(models.TextChoices):
    """
    A model to store the type of the improved user message.
    """

    GRAMMAR_AND_SPELLING = "GRAMMAR_AND_SPELLING", _("Grammar and spelling")
    MORE_EMPATHY = "MORE_EMPATHY", _("More empathy")
    CLARITY = "CLARITY", _("Clarity")
