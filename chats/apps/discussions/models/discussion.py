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
        content = content or self.serialized_ws_data
        self.notify(action=action, content=content, groups=[f"queue_{self.queue.pk}"])

    def check_queued(self):
        if self.is_queued and self.added_users.count() > 1:
            self.is_queued = False
            self.save()
            self.notify_queue("update")

    # permission block
    def get_permission(self, user):
        return self.project.get_permission(user)

    def can_add_user(self, user_permission) -> bool:
        if user_permission.is_manager(any_sector=True):
            return True
        return self.added_users.count() < settings.DISCUSSION_AGENTS_LIMIT

    def is_admin_manager_or_creator(self, user):
        perm = self.get_permission(user)
        try:
            return perm.is_manager(any_sector=True) or self.created_by == user
        except AttributeError:
            return False

    def is_added_user(self, user):
        return self.added_users.filter(permission__user=user).exists()

    def can_retrieve(self, user):
        if self.is_added_user(user):
            return True
        if self.is_admin_manager_or_creator(user):
            return True
        if (
            self.is_queued
            and self.queue.authorizations.filter(permission__user=user).exists()
        ):
            return True

        return False

    # messages and discussion users
    def create_discussion_user(self, from_user, to_user, role=None):
        from_permission = self.get_permission(user=from_user)
        to_permission = self.get_permission(user=to_user)
        discussion_user = None

        if (from_permission and to_permission) and self.can_add_user(from_permission):
            role = role if role is not None else to_permission.role
            discussion_user = self.added_users.create(
                permission=to_permission, role=role
            )
            self.check_queued()
            self.notify_user(action="update", user_permission=to_permission)

        return discussion_user

    def create_discussion_message(self, message, user=None, system=False, notify=True):
        sender = (user or self.created_by) if not system else None
        msg = self.messages.create(user=sender, text=message)
        if notify:
            msg.notify("create")
        return msg
