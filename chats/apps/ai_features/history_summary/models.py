from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.apps.accounts.models import User
from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.rooms.models import Room
from chats.core.models import BaseModel


class HistorySummaryStatus(models.TextChoices):
    """
    A model to store the status of the history summary.
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    UNAVAILABLE = "UNAVAILABLE"


class HistorySummary(BaseModel):
    """
    A model to store the history summary of a room.
    """

    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12,
        choices=HistorySummaryStatus.choices,
        default=HistorySummaryStatus.PENDING,
    )
    summary = models.TextField(null=True, blank=True)
    feature_prompt = models.ForeignKey(
        FeaturePrompt, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = _("History Summary")
        verbose_name_plural = _("History Summaries")

    def __str__(self):
        return f"{self.room.pk} - {self.status}"

    def update_status(self, status: HistorySummaryStatus):
        self.status = status
        self.save(update_fields=["status"])


class HistorySummaryFeedback(BaseModel):
    """
    A model to store the user feedback of the history summary.
    """

    history_summary = models.ForeignKey(
        HistorySummary,
        verbose_name=_("History Summary"),
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    user = models.ForeignKey(
        User,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
        related_name="history_summary_feedbacks",
    )
    liked = models.BooleanField(_("Liked?"))
    feedback = models.CharField(_("Feedback"), max_length=150, blank=True, null=True)

    class Meta:
        verbose_name = _("History Summary Feedback")
        verbose_name_plural = _("History Summary Feedbacks")
        constraints = [
            models.UniqueConstraint(
                fields=["history_summary", "user"],
                name="unique_history_summary_user_feedback",
            )
        ]

    def __str__(self):
        return f"{self.history_summary.pk} - {self.user.email}"
