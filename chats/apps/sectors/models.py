from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group


class Sector(BaseModel):
    name = models.CharField(_("name"), max_length=120)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("sectors"),
        related_name="sectors",
        on_delete=models.CASCADE,
        to_field="uuid",
    )
    rooms_limit = models.PositiveIntegerField(_("Rooms limit per employee"))
    work_start = models.TimeField(_("work start"), auto_now=False, auto_now_add=False)
    work_end = models.TimeField(_("work end"), auto_now=False, auto_now_add=False)
    is_deleted = models.BooleanField(_("is deleted?"), default=False)

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    @property
    def manager_authorizations(self):
        return self.authorizations.filter(role=2)

    @property
    def employee_pks(self):
        return list(self.authorizations.all().values_list("user__pk", flat="True"))

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
        return self.authorizations.filter(role=SectorAuthorization.ROLE_AGENT).count()

    @property
    def contact_count(self):
        qs = (
            self.rooms.filter(contact__isnull=False)
            .order_by("contact")
            .distinct()
            .count()
        )
        return qs

    def get_or_create_user_authorization(self, user):
        sector_auth, created = self.authorizations.get_or_create(user=user)

        return sector_auth

    def set_user_authorization(self, user, role: int):
        sector_auth, created = self.authorizations.get_or_create(user=user, role=role)
        return sector_auth

    def get_permission(self, user):
        try:
            sector_auth = self.authorizations.get(user=user)
        except SectorAuthorization.DoesNotExist:
            sector_auth = self.project.authorizations.get(user=user, role=1)
        return sector_auth

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


class SectorAuthorization(BaseModel):
    ROLE_NOT_SETTED = 0
    ROLE_AGENT = 1
    ROLE_MANAGER = 2

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_AGENT, _("admin")),
        (ROLE_MANAGER, _("manager")),
    ]

    user = models.ForeignKey(
        "accounts.User",
        related_name="sector_authorizations",
        verbose_name=_("User"),
        on_delete=models.CASCADE,
    )

    sector = models.ForeignKey(
        Sector,
        related_name="authorizations",
        verbose_name=_("Sector"),
        to_field="uuid",
        on_delete=models.CASCADE,
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_AGENT
    )

    class Meta:
        verbose_name = _("Sector Authorization")
        verbose_name_plural = _("Sector Authorizations")
        unique_together = [
            "user",
            "sector",
        ]  # only one permission on the sector per user

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
    def is_agent(self):
        return self.role == self.ROLE_AGENT

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
            group_name=f"user_{self.user.pk}",
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
        to_field="uuid",
        on_delete=models.CASCADE,
    )

    def get_permission(self, user):
        return self.sector.get_permission(user)

    class Meta:
        verbose_name = _("Sector Tag")
        verbose_name_plural = _("Sector Tags")

    def __str__(self):
        return self.name
