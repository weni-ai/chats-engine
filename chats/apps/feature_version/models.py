from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class FeatureVersion(BaseModel):
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("Project"),
        related_name="feature_versions",
        on_delete=models.CASCADE,
    )
    feature_version = models.CharField(
        _("feature version id"), max_length=200, blank=True
    )
    sectors = models.JSONField(
        _("sectors list"),
        blank=True,
        null=True,
    )
