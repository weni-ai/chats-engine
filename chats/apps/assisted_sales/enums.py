from django.db import models
from django.utils.translation import gettext_lazy as _


class CopilotMessageFeedbackTags(models.TextChoices):
    """
    Text choices with the possible tags of the copilot message feedback.
    """

    INCORRECT_ANSWER = "incorrect_answer", _("Incorrect answer")
    INCOMPLETE_ANSWER = "incomplete_answer", _("Incomplete answer")
    CONFUSING_ANSWER = "confusing_answer", _("Confusing answer")
    NO_ITEMS_FOUND = "no_items_found", _("No items found")
    OUT_OF_CONTEXT_ITEMS = "out_of_context_items", _(
        "Suggested items were out of context"
    )
    DID_NOT_LOAD = "did_not_load", _("Did not load")
    SLOW_TO_LOAD = "slow_to_load", _("Took a long time to load")
    UNCLEAR_INTERFACE = "unclear_interface", _("Unclear interface")
