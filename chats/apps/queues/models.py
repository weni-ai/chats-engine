from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel, BaseSoftDeleteModel

User = get_user_model()


class Queue(BaseSoftDeleteModel, BaseModel):
    sector = models.ForeignKey(
        "sectors.Sector",
        verbose_name=_("sector"),
        related_name="queues",
        on_delete=models.CASCADE,
    )
    name = models.CharField(_("Name"), max_length=150, blank=True)
    default_message = models.TextField(
        _("Default queue message"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("Sector Queue")
        verbose_name_plural = _("Sector Queues")

        constraints = [
            models.UniqueConstraint(fields=["sector", "name"], name="unique_queue_name")
        ]

    def __str__(self):
        return self.name

    @property
    def queue(self):
        return self

    @property
    def limit(self):
        return self.sector.rooms_limit

    def get_permission(self, user):
        try:
            return self.sector.get_permission(user=user)
        except ObjectDoesNotExist:
            return None

    @property
    def agent_count(self):
        return self.authorizations.filter(role=QueueAuthorization.ROLE_AGENT).count()

    @property
    def agents(self):
        return User.objects.filter(
            project_permissions__queue_authorizations__queue=self
        )

    @property
    def online_agents(self):
        return self.agents.filter(
            project_permissions__status="ONLINE",
            project_permissions__project=self.sector.project,
        )  # TODO: Set this variable to ProjectPermission.STATUS_ONLINE

    @property
    def available_agents(self):
        online_agents = self.online_agents.annotate(
            active_rooms_count=models.Count(
                "rooms",
                filter=models.Q(
                    rooms__is_active=True, rooms__queue__sector=self.sector
                ),
            )
        )
        return online_agents.filter(active_rooms_count__lt=self.limit).order_by(
            "active_rooms_count"
        )

    def get_or_create_user_authorization(self, user):
        sector_auth, created = self.authorizations.get_or_create(permission__user=user)
        return sector_auth

    def set_queue_authorization(self, user, role: int):
        sector_auth, created = self.authorizations.get_or_create(
            permission__user=user, role=role
        )
        return sector_auth


class QueueAuthorization(BaseModel):
    ROLE_NOT_SETTED = 0
    ROLE_AGENT = 1

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_AGENT, _("agent")),
    ]

    queue = models.ForeignKey(
        Queue,
        verbose_name=_("Queue"),
        related_name="authorizations",
        on_delete=models.CASCADE,
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_AGENT
    )

    permission = models.ForeignKey(
        "projects.ProjectPermission",
        verbose_name=_("User"),
        related_name="queue_authorizations",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Sector Queue Authorization")
        verbose_name_plural = _("Sector Queues Authorization")
        constraints = [
            models.UniqueConstraint(
                fields=["queue", "permission"], name="unique_queue_auth"
            )
        ]

    def get_permission(self, user):
        try:
            return self.queue.get_permission(user)
        except ObjectDoesNotExist:
            return None

    @property
    def sector(self):
        return self.queue.sector

    @property
    def is_agent(self):
        return self.role == self.ROLE_AGENT

    @property
    def user(self):
        return self.permission.user

    @property
    def can_list(self):
        return self.is_agent
