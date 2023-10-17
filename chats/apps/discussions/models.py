from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel, BaseSoftDeleteModel


class DiscussionRoom(BaseModel, BaseSoftDeleteModel):
    room = models.ForeignKey(
        "rooms.Room",
        related_name="discussions",
        verbose_name=_("room discussion"),
        on_delete=models.CASCADE,
    )

    ended_at = models.DateTimeField(
        _("Ended at"), auto_now_add=False, null=True, blank=True
    )

    ended_by = models.CharField(_("Ended by"), max_length=50, null=True, blank=True)

    transfer_history = models.JSONField(_("Transfer History"), null=True, blank=True)


class DiscussionMessage(BaseModel):
    discussion_room = models.ForeignKey(
        "discussions.DiscussionRoom",
        related_name="discussion_message",
        verbose_name=_("message discussion"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="discussion_message",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    text = models.TextField(_("Text"), blank=True, null=True)


class DiscussionUser(BaseModel):
    user = models.ForeignKey(
        "accounts.User",
        related_name="discussion_user",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )

    discussion_room = models.ForeignKey(
        "discussions.DiscussionRoom",
        related_name="discussion_user",
        verbose_name=_("user discussion"),
        on_delete=models.CASCADE,
    )
