import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.core.managers import SoftDeletableManager
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
        return hasattr(self, "modified_by") and bool(self.modified_by)


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

    def deleted_sufix(self):
        name_sufix = "_is_deleted_" + str(timezone.now())
        return name_sufix

    def delete(self):
        self.is_deleted = True
        if hasattr(self, "name"):
            self.name += self.deleted_sufix()
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


class AuditableMixin(models.Model):
    """
    Tracks who created, last modified, and deleted each record.
    Fields are populated explicitly in views:
        serializer.save(created_by=request.user, modified_by=request.user)

    Audit persistence is gated by the AUDIT_LOG_FEATURE_FLAG_KEY flag for the
    record's project:
        - Flag ON: audit values provided by the caller are persisted.
        - Flag OFF on create: audit values are dropped (fields stay NULL).
        - Flag OFF on update: audit values provided by the caller are ignored
          and the original values loaded from the database are restored, so
          that historical audit data is never erased just because the flag
          was toggled off after the record existed.

    If the record has no project available (e.g. QuickMessage without sector),
    the flag cannot be evaluated and the mixin behaves as if the flag was OFF
    (fail-closed). If the flag service itself is unreachable or raises, the
    mixin fails open and keeps the caller-provided values.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        on_delete=models.SET_NULL,
        verbose_name=_("Created by"),
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        on_delete=models.SET_NULL,
        verbose_name=_("Modified by"),
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        on_delete=models.SET_NULL,
        verbose_name=_("Deleted by"),
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._snapshot_audit_ids()

    def _snapshot_audit_ids(self):
        self._audit_original_created_by_id = self.created_by_id
        self._audit_original_modified_by_id = self.modified_by_id
        self._audit_original_deleted_by_id = self.deleted_by_id

    def _get_project(self):
        """
        Returns the project associated with this instance.
        Models using this mixin must define a `project` attribute or property.
        """
        project = getattr(self, "project", None)
        if project is None:
            raise AttributeError(
                f"{self.__class__.__name__} must define a `project` attribute or property "
                "to use AuditableMixin."
            )
        return project

    def _is_audit_flag_active(self):
        try:
            project = self._get_project()
        except AttributeError:
            return False
        try:
            return is_feature_active_for_attributes(
                settings.AUDIT_LOG_FEATURE_FLAG_KEY,
                {"projectUUID": str(project.uuid)},
            )
        except Exception:
            return True

    def save(self, *args, **kwargs):
        if not self._is_audit_flag_active():
            if self._state.adding:
                self.created_by = None
                self.modified_by = None
                self.deleted_by = None
            else:
                self.created_by_id = self._audit_original_created_by_id
                self.modified_by_id = self._audit_original_modified_by_id
                self.deleted_by_id = self._audit_original_deleted_by_id

        super().save(*args, **kwargs)
        self._snapshot_audit_ids()
