import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from chats.utils.websockets import send_channels_group


class WebSocketsNotifiableMixin:
    @property
    def serialized_ws_data(self) -> dict:
        ...

    @property
    def notification_groups(self) -> list:
        ...

    def get_action(self, action: str) -> str:
        ...

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

    class Meta:
        abstract = True

    def deleted_sufix(self):
        name_sufix = "_is_deleted_" + str(timezone.now())
        return name_sufix

    def delete(self):
        self.is_deleted = True
        self.name += self.deleted_sufix()
        self.save()


class BaseConfigurableModel(models.Model):
    config = models.JSONField(_("config"), blank=True, null=True)

    class Meta:
        abstract = True
