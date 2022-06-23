from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class QuickMessage(BaseModel):
    user = models.ForeignKey(
        "accounts.User", verbose_name=_("quick_messages"), on_delete=models.CASCADE
    )
    shortcut = models.CharField(_("shortcut"), max_length=50)
    text = models.TextField(_("text"))

    class Meta:
        verbose_name = _("Quick Message")
        verbose_name_plural = _("Quick Messages")
