from django.db import models

from chats.core.models import BaseModel
from chats.apps.feedbacks.choices import FeedbackRate


class LastFeedbackShownToUser(BaseModel):
    """
    Last feedback shown to user model
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="last_feedback_shown_to_user",
    )
    last_shown_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Last feedback shown to user"
        verbose_name_plural = "Last feedback shown to users"

    def __str__(self):
        return f"Last feedback shown to {self.user.email} at {self.last_shown_at}"


class UserFeedback(BaseModel):
    """
    User feedback model
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="user_feedbacks",
    )
    rate = models.IntegerField(choices=FeedbackRate.choices)
    text = models.TextField(null=True, blank=True)
    project = models.ForeignKey(
        "projects.Project",
        related_name="user_feedbacks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "User Feedback"
        verbose_name_plural = "User Feedbacks"

    def __str__(self):
        return f"Feedback from {self.user.email} {self.rate}"
