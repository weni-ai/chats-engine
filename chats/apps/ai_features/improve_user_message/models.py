from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageStatusChoices,
    ImprovedUserMessageTypeChoices,
)


class MessageImprovementStatus(BaseModel):
    """
    A model to store the status of the improved user message.
    """

    message = models.ForeignKey(
        "msgs.Message",
        verbose_name=_("Message"),
        on_delete=models.CASCADE,
        related_name="improved_user_message_status",
        unique=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ImprovedUserMessageStatusChoices.choices,
    )
    type = models.CharField(
        _("Type"),
        max_length=20,
        choices=ImprovedUserMessageTypeChoices.choices,
    )

    class Meta:
        verbose_name = _("Message Improvement Status")
        verbose_name_plural = _("Message Improvement Statuses")

    def __str__(self):
        return f"{self.message.uuid} - {self.status} - {self.type}"
