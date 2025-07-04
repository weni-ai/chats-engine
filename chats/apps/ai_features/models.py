from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class FeaturePrompt(BaseModel):
    """
    A model to store the prompts for the features.
    """

    feature = models.CharField(_("Feature"), max_length=255)
    model = models.CharField(_("Model"), max_length=255)
    settings = models.JSONField(_("Settings"), null=True, blank=True)
    prompt = models.TextField(_("Prompt"))
    version = models.IntegerField(_("Version"), default=1)

    class Meta:
        unique_together = ("feature", "version")

        verbose_name = _("AI Feature Prompt")
        verbose_name_plural = _("AI Feature Prompts")

    def __str__(self):
        return f"{self.feature} - {self.version}"
