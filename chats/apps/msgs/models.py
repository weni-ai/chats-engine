from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group


class Message(BaseModel):
    room = models.ForeignKey(
        "rooms.Room",
        related_name="messages",
        verbose_name=_("room"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="messages",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        related_name="messages",
        verbose_name=_("contact"),
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

    def get_authorization(self, user):
        return self.room.get_authorization(user)

    def media(self):
        return self.medias.first()

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
        Message,
        related_name="medias",
        verbose_name=_("message"),
        on_delete=models.CASCADE,
    )
    media = models.FileField(_("url"), max_length=100)

    class Meta:
        verbose_name = _("MessageMedia")
        verbose_name_plural = _("MessageMedias")

    def __str__(self):
        return f"{self.message.pk} - {self.media}"

    @property
    def url(self):
        return self.media.url

    def get_authorization(self, user):
        return self.room.get_authorization(user)
