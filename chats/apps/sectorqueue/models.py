from django.db import models
from chats.core.models import BaseModel
from django.utils.translation import gettext_lazy as _
from chats.apps.sectors.models import Sector, SectorAuthorization


class SectorQueue(BaseModel):
    sector = models.ForeignKey(
        Sector,
        verbose_name=_("queues"),
        related_name="sector_authorizations",
        on_delete=models.CASCADE,
        to_field="uuid"
    )
    name = models.CharField(_("sector name"), max_length=150, blank=True)

    class Meta:
        verbose_name = _("Sector Queue")
        verbose_name_plural = _("Sector Queues")

    def __str__(self):
        return self.name

    def get_permission(self, user):
        try:
            sectorqueue_auth = self.sector.authorizations.get(user=user)
        except SectorAuthorization.DoesNotExist:
            if self.sector.project.authorizations.filter(user=user):
                sectorqueue_auth = True
            elif self.sector_authorizations.filter(user=user):
                sectorqueue_auth = True
            else:
                sectorqueue_auth = False
        return sectorqueue_auth

    @property
    def agent_count(self):
        return self.sector_authorizations.filter(role=SectorQueueAuthorization.ROLE_AGENT).count()


class SectorQueueAuthorization(BaseModel):
    ROLE_NOT_SETTED = 0
    ROLE_AGENT = 1

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_AGENT, _("agent")),
    ]

    queue = models.ForeignKey(
        SectorQueue,
        verbose_name=_("SectorQueueAutorization"),
        related_name="sector_authorizations",
        on_delete=models.CASCADE,
        to_field="uuid"
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_AGENT
    )

    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("SectorQueueAutorization"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Sector Queue Authorization")
        verbose_name_plural = _("Sector Queues Authorization")

    def __str__(self):
        return self.get_role_display()

    def get_permission(self, user):
        try:
            sectorqueue_auth = self.queue.sector.authorizations.get(user=user)
        except SectorAuthorization.DoesNotExist:
            if self.queue.sector.project.authorizations.filter(user=user):
                sectorqueue_auth = True
            elif self.queue.sector_authorizations.filter(user=user):
                sectorqueue_auth = True
            else:
                sectorqueue_auth = False
        return sectorqueue_auth

    @property
    def is_agent(self):
        return self.role == self.ROLE_AGENT

    @property
    def can_list(self):
        return self.is_agent
