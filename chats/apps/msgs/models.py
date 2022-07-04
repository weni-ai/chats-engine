from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group


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

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.msgs.serializers import MessageWSSerializer

        return MessageWSSerializer(self).data

    def notify_room(self, action):
        """ """
        send_channels_group(
            group_name=f"room_{self.room.pk}",
            type="notify",
            content=self.serialized_ws_data,
            action=f"msg.{action}",
        )


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
