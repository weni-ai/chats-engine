from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class DiscussionUser(BaseModel):
    class Role(models.IntegerChoices):
        CREATOR = 0, _("Creator")
        ADMIN = 1, _("Admin")
        PARTICIPANT = 2, _("Participant")

    permission = models.ForeignKey(
        "projects.ProjectPermission",
        related_name="discussion_users",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
    )
    discussion = models.ForeignKey(
        "discussions.Discussion",
        related_name="added_users",
        on_delete=models.CASCADE,
        verbose_name=_("Discussion"),
    )
    role = models.PositiveIntegerField(
        _("role"), choices=Role.choices, default=Role.PARTICIPANT
    )

    class Meta:
        verbose_name = "Discussion User"
        verbose_name_plural = "Discussions Users"
        constraints = [
            models.UniqueConstraint(
                fields=["permission", "discussion"],
                name="unique_permission_per_discussion",
            )
        ]

    def __str__(self) -> str:
        return f"{self.discussion.subject} {self.user.full_name} {self.role}"

    def notification_data(self) -> dict:
        return {
            "discussion": str(self.discussion.pk),
            "user": self.permission.user.full_name,
            "role": self.role,
        }

    @property
    def user(self):
        return self.permission.user
