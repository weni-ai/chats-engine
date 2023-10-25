from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel, BaseSoftDeleteModel


class Discussion(BaseSoftDeleteModel, BaseModel):
    subject = models.CharField(
        _("Subject Text"), max_length=50, blank=False, null=False
    )
    created_by = models.ForeignKey(
        "accounts.User",
        related_name="discussions",
        on_delete=models.CASCADE,
        verbose_name=_("Created By"),
        to_field="email",
    )
    room = models.ForeignKey(
        "rooms.Room",
        related_name="discussions",
        on_delete=models.CASCADE,
        verbose_name=_("Room"),
    )
    queue = models.ForeignKey(
        "queues.Queue",
        related_name="discussions",
        on_delete=models.CASCADE,
        verbose_name=_("Queue"),
    )
    is_queued = models.BooleanField(_("Is queued?"), default=True)
    is_active = models.BooleanField(_("Is active?"), default=True)

    class Meta:
        verbose_name = "Discussion"
        verbose_name_plural = "Discussions"

    def __str__(self) -> str:
        return f"{self.created_by.full_name} {self.subject}"


class DiscussionUser(BaseModel):
    class Role(models.IntegerChoices):
        CREATOR = 0, _("Creator")
        ADMIN = 1, _("Admin")
        PARTICIPANT = 2, _("Participant")

    user = models.ForeignKey(
        "accounts.User",
        related_name="discussion_user",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        to_field="email",
    )
    discussion = models.ForeignKey(
        Discussion,
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

    def __str__(self) -> str:
        return f"{self.discussion.subject} {self.user.full_name} {self.role}"


class DiscussionMessage(BaseModel):
    discussion = models.ForeignKey(
        "discussions.Discussion",
        related_name="messages",
        verbose_name=_("discussion"),
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
        "accounts.User",
        related_name="discussion_messages",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    text = models.TextField(_("Text"), blank=True, null=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_on"]
