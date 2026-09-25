from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel

FEEDBACK_TEXT_MAX_LENGTH = 150


class CopilotIntegration(BaseModel):
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("Live Desk project"),
        on_delete=models.CASCADE,
        related_name="copilot_integrations",
    )
    sector = models.ForeignKey(
        "sectors.Sector",
        verbose_name=_("Sector"),
        on_delete=models.CASCADE,
        related_name="copilot_integrations",
        null=True,
        blank=True,
    )
    copilot_project_uuid = models.UUIDField(_("Copilot project UUID"))
    name = models.CharField(_("Name"), max_length=255)
    assigned_agents = models.PositiveIntegerField(_("Assigned agents"), default=0)
    connection = models.JSONField(_("Connection"), default=dict)
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Connected by"),
        on_delete=models.SET_NULL,
        related_name="copilot_integrations",
        null=True,
        blank=True,
    )
    connected_on = models.DateTimeField(_("Connected on"), auto_now_add=True)
    copilot_created_on = models.DateTimeField(
        _("Copilot created on"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("Copilot integration")
        verbose_name_plural = _("Copilot integrations")
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(sector__isnull=True),
                name="unique_copilot_per_project_without_sector",
            ),
            models.UniqueConstraint(
                fields=["sector"],
                condition=Q(sector__isnull=False),
                name="unique_copilot_per_sector",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.copilot_project_uuid})"


class CopilotMessageFeedback(BaseModel):
    """
    A model to store the user feedback of a Copilot assistant message.
    """

    room = models.ForeignKey(
        "rooms.Room",
        verbose_name=_("Room"),
        on_delete=models.CASCADE,
        related_name="copilot_message_feedbacks",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
        related_name="copilot_message_feedbacks",
    )
    message_id = models.CharField(_("Message ID"), max_length=255)
    liked = models.BooleanField(_("Liked?"))
    text = models.CharField(
        _("Text"), max_length=FEEDBACK_TEXT_MAX_LENGTH, blank=True, default=""
    )
    tags = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        verbose_name=_("Tags"),
    )

    class Meta:
        verbose_name = _("Copilot message feedback")
        verbose_name_plural = _("Copilot message feedbacks")
        constraints = [
            models.UniqueConstraint(
                fields=["room", "message_id", "user"],
                name="unique_copilot_message_feedback_per_user",
            )
        ]

    def __str__(self):
        return f"{self.room_id} - {self.message_id} - {self.user}"
