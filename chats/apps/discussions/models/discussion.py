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
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "room",
                ],
                condition=models.Q(is_active=True),
                name="unique_room_is_activetrue_discussion",
            )
        ]

    def __str__(self) -> str:
        return f"{self.created_by.full_name} {self.subject}"

    def delete(self):
        self.is_active = False
        self.save()
        self.notify("close")

    @property
    def project(self):
        return self.queue.sector.project

    @property
    def sector(self):
        return self.queue.sector

    @property
    def serialized_ws_data(self):
        from ..serializers.discussions import DiscussionListSerializer  # noqa

        return DiscussionListSerializer(self).data

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

    def notify_user(self, user_permission, action: str, content: dict = {}):
        if "." not in action:
            action = f"discussions.{action}"
        content = content or self.serialized_ws_data
        send_channels_group(
            group_name=f"permission_{user_permission.pk}",
            call_type="notify",
            content=content,
            action=action,
        )

    def notify_users(self, action: str, content: dict = {}):
        if "." not in action:
            action = f"discussions.{action}"
        content = content or self.serialized_ws_data
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
        content = content or self.serialized_ws_data
        send_channels_group(
            group_name=f"queue_{self.queue.pk}",
            call_type="notify",
            content=content,
            action=action,
        )

    def notify(self, action: str, content: dict = {}, to_queue=False):
        if self.is_queued or to_queue:
            self.notify_queue(action=action, content=content)
        else:
            self.notify_users(action=action, content=content)

    def check_queued(self):
        if self.is_queued and self.added_users.count() > 1:
            self.is_queued = False
            self.save()
            self.notify_queue("update")
            self.notify_users("update")

    def can_add_user(self, user_permission) -> bool:
        if user_permission.is_manager(any_sector=True):
            return True
        return self.added_users.count() < settings.DISCUSSION_AGENTS_LIMIT

    def create_discussion_user(self, from_user, to_user, role=None):
        from_permission = self.get_permission(user=from_user)
        to_permission = self.get_permission(user=to_user)
        discussion_user = None

        if (from_permission and to_permission) and self.can_add_user(from_permission):
            role = role if role is not None else to_permission.role
            discussion_user = self.added_users.create(
                permission=to_permission, role=role
            )
            discussion_user.notify("create")
            self.check_queued()
        return discussion_user

    def create_discussion_message(self, message, user=None, system=False):
        sender = (user or self.created_by) if not system else None
        msg = self.messages.create(user=sender, text=message)
        msg.notify("create")
        return msg

    def get_permission(self, user):
        return self.project.get_permission(user)

    def is_admin_manager_or_creator(self, user):
        perm = self.get_permission(user)
        return perm.is_manager(any_sector=True) or self.created_by == user

    def can_retrieve(self, user):
        if self.added_users.filter(permission__user=user).exists():
            return True

        return self.is_admin_manager_or_creator(user)


class DiscussionUser(BaseModel):
    class Role(models.IntegerChoices):
        CREATOR = 0, _("Creator")
        ADMIN = 1, _("Admin")
        PARTICIPANT = 2, _("Participant")

    permission = models.ForeignKey(
        "projects.ProjectPermission",
        related_name="discussion_users",
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
        constraints = [
            models.UniqueConstraint(
                fields=["permission", "discussion"],
                name="unique_permission_per_discussion",
            )
        ]

    def __str__(self) -> str:
        return f"{self.discussion.subject} {self.user.full_name} {self.role}"

    def notification_data(self) -> dict:
        return {
            "discussion": str(self.discussion.pk),
            "user": self.permission.user.full_name,
            "role": self.role,
        }

    def notify(self, action: str):
        data = self.notification_data
        self.discussion.notify_user(
            user_permission=self.permission, content=data, action=f"d_user.{action}"
        )

    @property
    def user(self):
        return self.permission.user
