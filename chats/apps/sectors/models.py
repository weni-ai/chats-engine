import email
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from chats.apps.queues.models import QueueAuthorization

from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group
from django.db.models import F, Q


User = get_user_model()


class Sector(BaseModel):
    name = models.CharField(_("name"), max_length=120)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("Project"),
        related_name="sectors",
        on_delete=models.CASCADE,
    )
    rooms_limit = models.PositiveIntegerField(_("Rooms limit per employee"))
    work_start = models.TimeField(_("work start"), auto_now=False, auto_now_add=False)
    work_end = models.TimeField(_("work end"), auto_now=False, auto_now_add=False)
    is_deleted = models.BooleanField(_("is deleted?"), default=False)

    class Meta:
        verbose_name = _("Sector")
        verbose_name_plural = _("Sectors")

        constraints = [
            models.CheckConstraint(
                check=Q(work_end__gt=F("work_start")),
                name="wordend_greater_than_workstart_check",
            ),
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_sector_name"
            ),
            models.CheckConstraint(
                check=Q(rooms_limit__gt=0), name="rooms_limit_greater_than_zero"
            ),
        ]

    @property
    def sector(self):
        return self

    @property
    def manager_authorizations(self):
        return self.authorizations.all()

    @property
    def employee_pks(self):
        return list(self.authorizations.all().values_list("user__pk", flat="True"))

    @property
    def rooms(self):
        return self.queues.values("rooms")

    @property
    def active_rooms(self):
        return self.rooms.filter(is_active=True)

    @property
    def deactivated_rooms(self):
        return self.rooms.filter(is_active=True)

    @property
    def open_active_rooms(self):
        return self.rooms.filter(user__isnull=True, is_active=True)

    @property
    def closed_active_rooms(self):
        return self.rooms.filter(user__isnull=False, is_active=True)

    @property
    def open_deactivated_rooms(self):
        return self.rooms.filter(user__isnull=True, is_active=False)

    @property
    def vacant_deactivated_rooms(self):
        return self.rooms.filter(user__isnull=False, is_active=False)

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.sectors.serializers import SectorWSSerializer

        return SectorWSSerializer(self).data

    @property
    def agent_count(self):
        agents_count = list(
            self.queues.annotate(
                agents=models.Count(
                    "authorizations", filter=models.Q(authorizations__role=1)
                )
            ).values_list("agents", flat=True)
        )
        agents_count = sum(agents_count)
        return agents_count

    @property
    def queue_agents(self):
        return User.objects.filter(
            project_permissions__queue_authorizations__queue__pk__in=self.queues.values_list("pk", flat=True),
            project_permissions__queue_authorizations__role=QueueAuthorization.ROLE_AGENT
        ).distinct()

    @property
    def contact_count(self):
        # qs = (
        #     self.rooms.filter(contact__isnull=False)
        #     .order_by("contact")
        #     .distinct()
        #     .count()
        # )
        return 0

    def get_or_create_user_authorization(self, user):
        sector_auth, created = self.authorizations.get_or_create(user=user)

        return sector_auth

    def set_user_authorization(self, user, role: int):
        sector_auth, created = self.authorizations.get_or_create(user=user, role=role)
        return sector_auth

    def get_permission(self, user):
        return self.project.permissions.get(user=user)

    def notify_sector(self, action):
        """ """
        send_channels_group(
            group_name=f"sector_{self.pk}",
            type="notify",
            content=self.serialized_ws_data,
            action=f"sector.{action}",
        )

    def add_users_group(self):
        for auth in self.authorizations.filter(role__gte=1):
            auth.notify_user("created")

    def is_attending(self):
        tz = pendulum.timezone(str(self.project.timezone))
        created_on = pendulum.parse(str(self.created_on)).in_timezone(tz)
        work_start = self.work_start
        work_end = self.work_end
        
        return work_start < created_on < work_end


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
        return self.is_agent or self.is_manager

    @property
    def can_edit(self):
        return self.is_manager

    def get_permission(self, user):
        return self.sector.get_permission(user=user)

    def notify_user(self, action):
        """ """
        send_channels_group(
            group_name=f"user_{self.permission.user.pk}",
            type="notify",
            content=self.serialized_ws_data,
            action=f"sector_authorization.{action}",
        )


class SectorTag(BaseModel):

    name = models.CharField(_("Name"), max_length=120)
    sector = models.ForeignKey(
        "sectors.Sector",
        verbose_name=_("Sector"),
        related_name="tags",
        on_delete=models.CASCADE,
    )

    def get_permission(self, user):
        return self.sector.get_permission(user)

    class Meta:
        verbose_name = _("Sector Tag")
        verbose_name_plural = _("Sector Tags")

        constraints = [
            models.UniqueConstraint(fields=["sector", "name"], name="unique_tag_name")
        ]

    def __str__(self):
        return self.name
