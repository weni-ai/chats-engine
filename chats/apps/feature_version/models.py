from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class IntegratedFeature(BaseModel):
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("Project"),
        related_name="feature_versions",
        on_delete=models.CASCADE,
    )
    feature = models.CharField(_("feature uuid"), max_length=200, blank=True)
    current_version = models.JSONField(
        _("sectors list"),
        blank=True,
        null=True,
    )
