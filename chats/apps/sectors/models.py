import logging
from datetime import timedelta

import pendulum
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, F, Q, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from chats.apps.queues.utils import start_queue_priority_routing
from chats.core.models import BaseConfigurableModel, BaseModel, BaseSoftDeleteModel
from chats.utils.websockets import send_channels_group

from .sector_managers import SectorManager

User = get_user_model()

logger = logging.getLogger(__name__)


class Sector(BaseSoftDeleteModel, BaseConfigurableModel, BaseModel):
    name = models.CharField(_("name"), max_length=120)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("Project"),
        related_name="sectors",
        on_delete=models.CASCADE,
    )
    rooms_limit = models.PositiveIntegerField(_("Rooms limit per employee"))
    work_start = models.TimeField(
        _("work start"), auto_now=False, auto_now_add=False, null=True, blank=True
    )
    work_end = models.TimeField(
        _("work end"), auto_now=False, auto_now_add=False, null=True, blank=True
    )
    can_trigger_flows = models.BooleanField(
        _("Can trigger flows?"),
        help_text=_(
            "Is it possible to trigger flows(weni flows integration) from this sector?"
        ),
        default=False,
    )
    sign_messages = models.BooleanField(_("Sign messages?"), default=False)
    is_deleted = models.BooleanField(_("is deleted?"), default=False)
    open_offline = models.BooleanField(
        _("Open room when all agents are offline?"), default=True
    )
    can_edit_custom_fields = models.BooleanField(
        _("Can edit custom fields?"), default=False
    )

    working_day = models.JSONField(_("working_day"), blank=True, null=True)

    automatic_message_text = models.TextField(
        _("automatic message text"), blank=True, null=True
    )
    is_automatic_message_active = models.BooleanField(
        _("is automatic message active?"), default=False
    )

    tracker = FieldTracker(fields=["rooms_limit"])

    objects = SectorManager()
    all_objects = SectorManager(include_deleted=True)

    class Meta:
        verbose_name = _("Sector")
        verbose_name_plural = _("Sectors")

        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_sector_name"
            ),
        ]

    @property
    def external_token(self):
        return self.project.external_token

    @property
    def completion_context(self):
        try:
            can_input_context = self.config.get("can_input_context")
            if can_input_context:
                return self.config.get("completion_context")
            return None
        except AttributeError:
            return None

    @property
    def can_use_chat_completion(self) -> bool:
        try:
            return self.config.get("can_use_chat_completion")
        except AttributeError:
            return False

    @property
    def sector(self):
        return self

    @property
    def manager_authorizations(self):
        return self.authorizations.all()

    @property
    def employee_pks(self):
        return list(
            self.authorizations.all().values_list("permission__user__pk", flat="True")
        )

    @property
    def rooms(self):
        return self.queues.values("rooms")

    @property
    def active_rooms(self):
        return self.rooms.filter(rooms__is_active=True)

    @property
    def deactivated_rooms(self):
        return self.rooms.filter(rooms__is_active=False)

    @property
    def open_active_rooms(self):
        return self.rooms.filter(rooms__user__isnull=True, rooms__is_active=True)

    @property
    def closed_active_rooms(self):
        return self.rooms.filter(rooms__user__isnull=False, rooms__is_active=True)

    @property
    def open_deactivated_rooms(self):
        return self.rooms.filter(rooms__user__isnull=True, rooms__is_active=False)

    @property
    def vacant_deactivated_rooms(self):
        return self.rooms.filter(rooms__user__isnull=False, rooms__is_active=False)

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.sectors.serializers import SectorWSSerializer

        return SectorWSSerializer(self).data

    @property
    def agent_count(self):
        agents_count = (
            self.queues.filter(authorizations__role=1, is_deleted=False)
            .values_list("authorizations__permission", flat=True)
            .distinct()
            .count()
        )
        return agents_count

    @property
    def queue_agents(self):
        return User.objects.filter(
            project_permissions__project=self.project,
            project_permissions__queue_authorizations__isnull=False,
        ).distinct()

    @property
    def managers(self):
        return User.objects.filter(
            project_permissions__sector_authorizations__sector=self
        )

    @property
    def online_managers(self):
        return User.objects.filter(
            project_permissions__sector_authorizations__sector=self,
            project_permissions__status="ONLINE",
        )

    @property
    def contact_count(self):
        # qs = (
        #     self.rooms.filter(contact__isnull=False)
        #     .order_by("contact")
        #     .distinct()
        #     .count()
        # )
        return 0

    @property
    def template_type_setup(self):
        return {
            "name": self.name,
            "rooms_limit": self.rooms_limit,
            "work_start": str(self.work_start),
            "work_end": str(self.work_end),
            "can_trigger_flows": self.can_trigger_flows,
            "sign_messages": self.sign_messages,
            "open_offline": self.open_offline,
            "can_edit_custom_fields": self.can_edit_custom_fields,
            "config": self.config,
            "queues": list(
                self.queues.filter(is_deleted=False).values(
                    "name", "default_message", "config"
                )
            ),
        }

    def validate_agent_status(self, queue=None):
        if self.open_offline:
            return True
        is_online = False
        if queue:
            is_online = queue.authorizations.filter(
                permission__status="ONLINE"
            ).exists()
        else:
            is_online = (
                self.queues.annotate(
                    online_count=Count(
                        "authorizations",
                        filter=Q(authorizations__permission__status="ONLINE"),
                    )
                )
                .filter(online_count__gt=0)
                .exists()
            )

        return is_online

    def is_attending(self, created_on):
        """
        Backwards-compat boolean: now delegates to working_hours config.
        Returns True if creation time is allowed by working_hours, False otherwise.
        """
        tz = pendulum.timezone(str(self.project.timezone))
        created_on = (
            pendulum.instance(created_on)
            if not isinstance(created_on, pendulum.DateTime)
            else created_on
        )
        created_on = (
            tz.localize(created_on)
            if created_on.tzinfo is None
            else created_on.in_timezone(tz)
        )
        try:
            from chats.apps.sectors.utils import working_hours_validator

            working_hours_validator.validate_working_hours(self, created_on)
            return True
        except Exception:
            return False

    def get_or_create_user_authorization(self, user):
        sector_auth, created = self.authorizations.get_or_create(user=user)

        return sector_auth

    def set_user_authorization(self, permission, role: int):
        sector_auth, created = self.authorizations.get_or_create(
            permission=permission, role=role
        )
        return sector_auth

    def get_permission(self, user):
        try:
            return self.project.get_permission(user=user)
        except ObjectDoesNotExist:
            return None

    def is_manager(self, user):
        perm = self.get_permission(user=user)
        return perm.is_admin or self.authorizations.filter(permission=perm).exists()

    def save(self, *args, **kwargs):
        # Detecting if the rooms limit has increased.
        # If so, we need to trigger the queue priority routing for all queues in the sector,
        # to distribute the rooms among the available agents.
        should_trigger_queue_priority_routing = False

        if (
            self.project.use_queue_priority_routing
            and self.tracker.has_changed("rooms_limit")
            and self.rooms_limit > self.tracker.previous("rooms_limit")
        ):
            should_trigger_queue_priority_routing = True

        super().save(*args, **kwargs)

        if should_trigger_queue_priority_routing:
            logger.info(
                "Rooms limit increased for sector %s (%s), triggering queue priority routing",
                self.name,
                self.pk,
            )
            for queue in self.queues.all():
                start_queue_priority_routing(queue)

    def delete(self):
        super().delete()
        self.queues.filter(is_deleted=False).update(
            is_deleted=True, name=Concat(F("name"), Value(self.deleted_sufix()))
        )


class SectorAuthorization(BaseModel):
    ROLE_NOT_SETTED = 0
    ROLE_MANAGER = 1

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_MANAGER, _("manager")),
    ]
    # TODO: CONSTRAINT >  A user can only have one auth per sector
    permission = models.ForeignKey(
        "projects.ProjectPermission",
        related_name="sector_authorizations",
        verbose_name=_("User"),
        on_delete=models.CASCADE,
    )

    sector = models.ForeignKey(
        Sector,
        related_name="authorizations",
        verbose_name=_("Sector"),
        on_delete=models.CASCADE,
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_NOT_SETTED
    )

    class Meta:
        verbose_name = _("Sector Authorization")
        verbose_name_plural = _("Sector Authorizations")
        constraints = [
            models.UniqueConstraint(
                fields=["sector", "permission"], name="unique_sector_auth"
            )
        ]

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.sectors.serializers import (
            SectorAuthorizationWSSerializer,
        )

        return SectorAuthorizationWSSerializer(self).data

    @property
    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    @property
    def is_authorized(self):
        return self.is_manager

    @property
    def can_edit(self):
        return self.is_manager

    def get_permission(self, user):
        try:
            return self.sector.get_permission(user=user)
        except ObjectDoesNotExist:
            return None

    def notify_user(self, action):
        """ """
        send_channels_group(
            group_name=f"permission_{self.permission.user.pk}",
            call_type="notify",
            content=self.serialized_ws_data,
            action=f"sector_authorization.{action}",
        )

    @property
    def project(self):
        return self.sector.project


class SectorTag(BaseModel):
    name = models.CharField(_("Name"), max_length=120)
    sector = models.ForeignKey(
        "sectors.Sector",
        verbose_name=_("Sector"),
        related_name="tags",
        on_delete=models.CASCADE,
    )

    def get_permission(self, user):
        try:
            return self.sector.get_permission(user)
        except ObjectDoesNotExist:
            return None

    class Meta:
        verbose_name = _("Sector Tag")
        verbose_name_plural = _("Sector Tags")
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(fields=["sector", "name"], name="unique_tag_name")
        ]

    def __str__(self):
        return self.name

    @property
    def project(self):
        return self.sector.project


class SectorGroupSector(BaseModel):
    sector_group = models.ForeignKey(
        "GroupSector",
        related_name="sector_group_sectors",
        on_delete=models.CASCADE,
    )
    sector = models.ForeignKey(
        Sector,
        related_name="sector_group_sectors",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Sector Group Sector")
        verbose_name_plural = _("Sector Group Sectors")
        constraints = [
            models.UniqueConstraint(
                fields=["sector_group", "sector"],
                name="unique_sector_group_sector",
            )
        ]

    def __str__(self):
        return f"{self.sector_group.name} - {self.sector.name}"


class GroupSector(BaseModel, BaseSoftDeleteModel):
    name = models.CharField(_("Name"), max_length=120)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("Project"),
        related_name="group_sectors",
        on_delete=models.CASCADE,
    )
    sectors = models.ManyToManyField(
        Sector,
        through=SectorGroupSector,
        related_name="group_sectors",
        blank=True,
    )
    rooms_limit = models.PositiveIntegerField(_("Rooms limit per employee"))

    class Meta:
        verbose_name = _("Group Sector")
        verbose_name_plural = _("Group Sectors")

    def __str__(self):
        return self.name

    def get_sectors(self):
        return self.sectors.all()

    def get_permission(self, user):
        try:
            return self.project.get_permission(user)
        except ObjectDoesNotExist:
            return None


class GroupSectorAuthorization(BaseModel):
    ROLE_NOT_SETTED = 0
    ROLE_MANAGER = 1
    ROLE_AGENT = 2

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_MANAGER, _("manager")),
        (ROLE_AGENT, _("agent")),
    ]
    group_sector = models.ForeignKey(
        "GroupSector",
        related_name="group_sector_authorizations",
        on_delete=models.CASCADE,
    )
    permission = models.ForeignKey(
        "projects.ProjectPermission",
        related_name="group_sector_authorizations",
        on_delete=models.CASCADE,
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_NOT_SETTED
    )

    class Meta:
        verbose_name = _("Group Sector Authorization")
        verbose_name_plural = _("Group Sector Authorizations")
        constraints = [
            models.UniqueConstraint(
                fields=["group_sector", "permission", "role"],
                name="unique_group_sector_auth",
            )
        ]

    def __str__(self):
        return f"{self.group_sector.name} - {self.permission.user.email} - {self.role}"

    @property
    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    @property
    def is_agent(self):
        return self.role == self.ROLE_AGENT

    def get_permission(self, user):
        try:
            return self.group_sector.project.get_permission(user)
        except ObjectDoesNotExist:
            return None


class SectorHoliday(BaseSoftDeleteModel, BaseModel):
    """
    Model to store holidays and configurable special days by sector
    (feriados locais, folgas específicas, etc.)
    """

    CLOSED = "closed"
    CUSTOM_HOURS = "custom_hours"

    DAY_TYPE_CHOICES = [
        (CLOSED, _("Closed")),
        (CUSTOM_HOURS, _("Custom Hours")),
    ]

    sector = models.ForeignKey(
        Sector,
        verbose_name=_("Sector"),
        related_name="holidays",
        on_delete=models.CASCADE,
    )
    date = models.DateField(_("Date"))
    date_end = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("End date for holiday range"),
    )
    day_type = models.CharField(
        _("Day Type"), max_length=20, choices=DAY_TYPE_CHOICES, default=CLOSED
    )
    start_time = models.TimeField(
        _("Start Time"),
        null=True,
        blank=True,
        help_text=_("Leave empty if day is closed"),
    )
    end_time = models.TimeField(
        _("End Time"),
        null=True,
        blank=True,
        help_text=_("Leave empty if day is closed"),
    )
    description = models.CharField(
        _("Description"),
        max_length=255,
        blank=True,
        help_text=_("Holiday name or reason for special hours"),
    )
    its_custom = models.BooleanField(_("Is Custom"), default=False)
    repeat = models.BooleanField(_("Repeat Annually"), default=False)

    class Meta:
        verbose_name = _("Sector Holiday")
        verbose_name_plural = _("Sector Holidays")
        indexes = [
            models.Index(fields=["sector", "date"], name="idx_sector_holiday"),
        ]
        constraints = [
            models.UniqueConstraint(
                condition=Q(is_deleted=False),
                fields=["sector", "date"],
                name="unique_sector_holiday",
            ),
            models.CheckConstraint(
                check=Q(
                    Q(day_type="closed", start_time__isnull=True, end_time__isnull=True)
                    | Q(
                        day_type="custom_hours",
                        start_time__isnull=False,
                        end_time__isnull=False,
                    )
                ),
                name="valid_holiday_times",
            ),
            models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")) | Q(start_time__isnull=True),
                name="holiday_end_greater_than_start",
            ),
        ]
        ordering = ["date"]

    def __str__(self):
        if self.day_type == self.CLOSED:
            return f"{self.sector.name} - {self.date} (Closed)"
        return f"{self.sector.name} - {self.date} ({self.start_time}-{self.end_time})"

    def get_permission(self, user):
        return self.sector.get_permission(user)

    @property
    def project(self):
        return self.sector.project

    def is_closed(self):
        return self.day_type == self.CLOSED

    def is_within_hours(self, time):
        """Verifica se um horário está dentro do período configurado"""
        if self.is_closed():
            return False
        return self.start_time <= time <= self.end_time

    # Cache invalidation helpers
    def _iter_dates(self):
        start = self.date
        end = self.date_end or self.date
        cur = start
        while cur <= end:
            yield cur
            cur += timedelta(days=1)

    def _invalidate_cache(self):
        try:
            from chats.apps.sectors.utils import CacheClient

            cache_client = CacheClient()
            sector_uuid = str(self.sector.uuid)
            for d in self._iter_dates():
                cache_key = f"holiday:{sector_uuid}:{d}"
                cache_client.delete(cache_key)
        except Exception:
            pass

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        super().save(update_fields=["is_deleted"])
        self._invalidate_cache()
