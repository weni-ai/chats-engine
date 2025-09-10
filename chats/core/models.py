import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from chats.core.managers import SoftDeletableManager
from chats.utils.websockets import send_channels_group


class WebSocketsNotifiableMixin:
    @property
    def serialized_ws_data(self) -> dict: ...

    @property
    def notification_groups(self) -> list: ...

    def get_action(self, action: str) -> str: ...

    def notify(self, action: str, groups: list = [], content: dict = {}) -> None:
        if "." not in action:
            action = self.get_action(action)
        content = content if content else self.serialized_ws_data
        groups = groups if groups else self.notification_groups
        for group in groups:
            send_channels_group(
                group_name=group,
                call_type="notify",
                content=content,
                action=action,
            )


class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    created_on = models.DateTimeField(
        _("Created on"), editable=False, auto_now_add=True
    )
    modified_on = models.DateTimeField(_("Modified on"), auto_now=True)

    class Meta:
        abstract = True

    @property
    def edited(self) -> bool:
        return bool(self.modified_by)


class BaseModelWithManualCreatedOn(BaseModel):
    created_on = models.DateTimeField(
        _("Created on"), editable=False, default=timezone.now
    )

    class Meta:
        abstract = True


class BaseSoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(_("is deleted?"), default=False)

    objects = SoftDeletableManager()
    all_objects = SoftDeletableManager(include_deleted=True)

    class Meta:
        abstract = True

    def deleted_sufix(self, user=None):
        """
        Build the soft-delete suffix including timestamp and the user identifier.
        """
        timestamp = str(timezone.now())
        if user is None:
            user_ident = "system"
        else:
            user_ident = getattr(user, "email", None) or getattr(user, "uuid", None) or str(user)
        user_ident = str(user_ident).replace(" ", "_")
        return f"_is_deleted_{timestamp}_{user_ident}"

    def delete(self, user=None, *args, **kwargs):
        """
        Soft delete: mark as deleted and append suffix with timestamp and user.
        """
        self.is_deleted = True
        self.name += self.deleted_sufix(user)
        self.save()


class BaseConfigurableModel(models.Model):
    config = models.JSONField(_("config"), blank=True, null=True)

    class Meta:
        abstract = True

    def get_config(self, key: str, default: any = None) -> any:
        """
        Get a config value from the config field
        """
        config = self.config or {}
        return config.get(key, default)

    def set_config(self, key: str, value: any):
        """
        Set a config value in the config field
        """
        self.config = self.config or {}
        self.config[key] = value
        self.save(update_fields=["config"])


class BaseIntegrationConfigurableModel(models.Model):
    integration_config = models.JSONField(
        _("config to use in project integration"), blank=True, null=True, default=dict
    )

    class Meta:
        abstract = True
