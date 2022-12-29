import json
import requests


from django.db import models
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

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
    text = models.TextField(_("Text"), blank=True, null=True)
    seen = models.BooleanField(_("Was it seen?"), default=False)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def save(self, *args, **kwargs) -> None:
        if self.room.is_active is False:
            raise ValidationError({"detail": _("Closed rooms cannot receive messages")})
        if self.room.is_24h_valid is False and self.user is not None:
            raise ValidationError(
                {
                    "detail": _(
                        "You cannot send messages after 24h from the last contact message"
                    )
                }
            )

        return super().save(*args, **kwargs)

    @property
    def serialized_ws_data(self) -> dict:
        from chats.apps.api.v1.msgs.serializers import MessageWSSerializer

        return dict(MessageWSSerializer(self).data)

    def get_authorization(self, user):
        return self.room.get_authorization(user)

    def media(self):
        return self.medias.all()

    def get_sender(self):
        return self.user or self.contact

    def notify_room(self, action: str, callback: bool = False):
        """ """
        send_channels_group(
            group_name=f"room_{self.room.pk}",
            call_type="notify",
            content=self.serialized_ws_data,
            action=f"msg.{action}",
        )
        if self.room.callback_url and callback:
            requests.post(
                self.room.callback_url,
                data=json.dumps(
                    {"type": "msg.create", "content": self.serialized_ws_data},
                    sort_keys=True,
                    indent=1,
                    cls=DjangoJSONEncoder,
                ),
                headers={"content-type": "application/json"},
            )


class MessageMedia(BaseModel):
    message = models.ForeignKey(
        Message,
        related_name="medias",
        verbose_name=_("message"),
        on_delete=models.CASCADE,
    )
    content_type = models.CharField(_("Content Type"), max_length=50)
    media_file = models.FileField(
        _("Media File"), null=True, blank=True, max_length=100
    )
    media_url = models.URLField(_("Media url"), null=True, blank=True, max_length=200)

    class Meta:
        verbose_name = _("MessageMedia")
        verbose_name_plural = _("MessageMedias")

    def __str__(self):
        return f"{self.message.pk} - {self.url}"

    def save(self, *args, **kwargs) -> None:
        if self.message.room.is_active is False:
            raise ValidationError({"detail": _("Closed rooms cannot receive messages")})
        return super().save(*args, **kwargs)

    @property
    def url(self):
        url = self.media_file.url if self.media_file else self.media_url
        try:
            if url.startswith("/"):
                url = settings.ENGINE_BASE_URL + url
        except AttributeError:
            return ""
        return url

    def get_authorization(self, user):
        return self.room.get_authorization(user)

    def callback(self):
        """ """
        msg_data = self.message.serialized_ws_data
        msg_data["text"] = ""

        if self.message.room.callback_url:
            requests.post(
                self.message.room.callback_url,
                data=json.dumps(
                    {"type": "msg.create", "content": msg_data},
                    sort_keys=True,
                    indent=1,
                    cls=DjangoJSONEncoder,
                ),
                headers={"content-type": "application/json"},
            )

    def notify_room(self, *args, **kwargs):
        """ """
        self.message.notify_room(*args, **kwargs)
