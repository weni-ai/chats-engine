from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class Message(BaseModel):
    room = models.ForeignKey(
        "rooms.Room", verbose_name=_("messages"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("messages"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        verbose_name=_("messages"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    text = models.TextField(_("Text"))
    seen = models.BooleanField(_("Was it seen?"), default=False)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"


class MessageMedia(BaseModel):
    message = models.ForeignKey(
        Message, verbose_name=_("medias"), on_delete=models.CASCADE
    )
    url = models.URLField(_("url"), max_length=200)
    media_type = models.CharField(_("media type"), max_length=150)

    class Meta:
        verbose_name = _("MessageMedia")
        verbose_name_plural = _("MessageMedias")

    def __str__(self):
        return f"{self.message.pk} - {self.media_type}"
