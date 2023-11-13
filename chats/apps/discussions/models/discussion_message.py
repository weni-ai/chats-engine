from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class DiscussionMessage(BaseModel):
    discussion = models.ForeignKey(
        "discussions.Discussion",
        related_name="messages",
        verbose_name=_("discussion"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="discussion_messages",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    text = models.TextField(_("Text"), blank=True, null=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_on"]

    @property
    def serialized_ws_data(self):
        from ..serializers.discussion_message import (  # noqa
            DiscussionReadMessageSerializer,
        )

        return DiscussionReadMessageSerializer(self).data

    def notify(self, action: str):
        self.discussion.notify(
            content=self.serialized_ws_data, action=f"discussion_msg.{action}"
        )


class DiscussionMessageMedia(BaseModel):
    message = models.ForeignKey(
        "discussions.DiscussionMessage",
        related_name="medias",
        verbose_name=_("discussion message"),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    content_type = models.CharField(_("Content Type"), max_length=300)
    media_file = models.FileField(
        _("Media File"),
        null=True,
        blank=True,
        max_length=300,
        upload_to="discussionmedia/%Y/%m/%d/",
    )

    class Meta:
        verbose_name = _("Discussion Message Media")
        verbose_name_plural = _("Discussion Message Medias")

    def __str__(self):
        return f"{self.message.pk} - {self.url}"

    @property
    def url(self):
        url = self.media_file.url
        try:
            if url.startswith("/"):
                url = settings.ENGINE_BASE_URL + url
        except AttributeError:
            return ""
        return url

    def notify(self):
        self.message.notify("update")
