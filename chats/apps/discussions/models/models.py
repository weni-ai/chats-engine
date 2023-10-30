from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel, BaseSoftDeleteModel
from chats.utils.websockets import send_channels_group


class Discussion(BaseSoftDeleteModel, BaseModel):
    subject = models.CharField(
        _("Subject Text"), max_length=50, blank=False, null=False
    )
    created_by = models.ForeignKey(
        "accounts.User",
        related_name="discussions",
        on_delete=models.CASCADE,
        verbose_name=_("Created By"),
        to_field="email",
    )
    room = models.ForeignKey(
        "rooms.Room",
        related_name="discussions",
        on_delete=models.CASCADE,
        verbose_name=_("Room"),
    )
    queue = models.ForeignKey(
        "queues.Queue",
        related_name="discussions",
        on_delete=models.CASCADE,
        verbose_name=_("Queue"),
    )
    is_queued = models.BooleanField(_("Is queued?"), default=True)
    is_active = models.BooleanField(_("Is active?"), default=True)

    class Meta:
        verbose_name = "Discussion"
        verbose_name_plural = "Discussions"

    def __str__(self) -> str:
        return f"{self.created_by.full_name} {self.subject}"

    @property
    def notification_data(self):
        return {
            "uuid": str(self.uuid),
            "subject": self.subject,
            "created_by": self.created_by.full_name,
            "created_on": str(self.created_on),
            "contact": self.room.contact.name,
            "is_active": self.is_active,
            "is_queued": self.is_queued,
        }

    def base_notification(self, content, action):
        if self.user:
            permission = self.get_permission(self.user)
            group_name = f"permission_{permission.pk}"
        else:
            group_name = f"queue_{self.queue.pk}"

        send_channels_group(
            group_name=group_name,
            call_type="notify",
            content=content,
            action=action,
        )

    def notify_users(self, action: str, content: dict = {}):
        if "." not in action:
            action = f"discussions.{action}"
        content = content or self.notification_data
        for added_user in self.added_users.all():
            send_channels_group(
                group_name=f"permission_{added_user.permission.pk}",
                call_type="notify",
                content=content,
                action=action,
            )

    def notify_queue(
        self,
        action: str,
        content: dict = {},
    ):
        if "." not in action:
            action = f"discussions.{action}"
        content = content or self.notification_data
        send_channels_group(
            group_name=f"queue_{self.queue.pk}",
            call_type="notify",
            content=content,
            action=action,
        )

    def notify(self, action: str):
        if self.is_queued:
            self.notify_queue(action=action)
        self.notify_users(action=action)


class DiscussionUser(BaseModel):
    class Role(models.IntegerChoices):
        CREATOR = 0, _("Creator")
        ADMIN = 1, _("Admin")
        PARTICIPANT = 2, _("Participant")

    permission = models.ForeignKey(
        "projects.ProjectPermission",
        related_name="discussion_user",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
    )
    discussion = models.ForeignKey(
        Discussion,
        related_name="added_users",
        on_delete=models.CASCADE,
        verbose_name=_("Discussion"),
    )
    role = models.PositiveIntegerField(
        _("role"), choices=Role.choices, default=Role.PARTICIPANT
    )

    class Meta:
        verbose_name = "Discussion User"
        verbose_name_plural = "Discussions Users"

    def __str__(self) -> str:
        return f"{self.discussion.subject} {self.user.full_name} {self.role}"


class DiscussionMessage(BaseModel):
    discussion = models.ForeignKey(
        "discussions.Discussion",
        related_name="messages",
        verbose_name=_("discussion"),
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
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
    def notification_data(self):
        sender = (
            None
            if not self.sender
            else dict(
                first_name=self.sender.first_name,
                last_name=self.sender.last_name,
                email=self.sender.email,
            )
        )

        medias = [
            dict(content_type=media.content_type, url=media.url)
            for media in self.medias.all()
        ]

        return {
            "uuid": str(self.uuid),
            "sender": sender,
            "discussion": str(self.discussion.pk),
            "text": self.text,
            "media": medias,
            "created_on": str(self.created_on),
        }

    def notify(self, action: str):
        data = self.notification_data
        self.discussion.notify(content=data, action=f"msg.{action}")


class DiscussionMessageMedia(BaseModel):
    message = models.ForeignKey(
        "discussions.DiscussionMessage",
        related_name="discussion_medias",
        verbose_name=_("discussion message"),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    content_type = models.CharField(_("Content Type"), max_length=300)
    media_file = models.FileField(
        _("Media File"), null=True, blank=True, max_length=300
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
