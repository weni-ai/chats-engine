from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class Log(BaseModel):
    class Action(models.TextChoices):
        CREATE = "CREATE", _("Create")
        UPDATE = "UPDATE", _("Update")
        DELETE = "DELETE", _("Delete")

    action = models.CharField(_("Action"), max_length=10, choices=Action.choices)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content type"),
    )
    object_id = models.UUIDField(_("Object ID"))
    content_object = GenericForeignKey("content_type", "object_id")
    changes = models.JSONField(_("Changes"), default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("User"),
    )
    extra_info = models.JSONField(_("Extra info"), default=dict, blank=True)
    request_info = models.JSONField(_("Request info"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Log")
        verbose_name_plural = _("Logs")
        indexes = [
            models.Index(
                fields=["content_type", "object_id"],
                name="logs_log_content_object_idx",
            ),
        ]
        ordering = ["-created_on"]

    def __str__(self):
        return f"{self.action} {self.content_type} {self.object_id}"
