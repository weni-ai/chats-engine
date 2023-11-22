from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel, BaseSoftDeleteModel, WebSocketsNotifiableMixin


class Discussion(BaseSoftDeleteModel, BaseModel, WebSocketsNotifiableMixin):
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
        # TODO: add serializer when creating discussion endpoints
        return {}

    @property
    def notification_groups(self) -> list:
        if self.is_queued:
            return [f"queue_{self.queue.pk}"]
        return [
            f"permission_{user_permission}"
            for user_permission in self.added_users.values_list("permission", flat=True)
        ]

    def get_action(self, action: str) -> str:
        return f"discussions.{action}"

    def notify_user(self, user_permission, action: str, content: dict = {}):
        if "." not in action:
            action = f"discussions.{action}"
        content = content or self.serialized_ws_data
        self.notify(
            action=action, content=content, groups=[f"permission_{user_permission.pk}"]
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
        return discussion_user

    def create_discussion_message(self, message, user=None, system=False, notify=True):
        sender = (user or self.created_by) if not system else None
        msg = self.messages.create(user=sender, text=message)
        if notify:
            msg.notify("create")
        return msg
