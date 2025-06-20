import random
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseConfigurableModel, BaseModel, BaseSoftDeleteModel

from .queue_managers import QueueManager

User = get_user_model()


class Queue(BaseSoftDeleteModel, BaseConfigurableModel, BaseModel):
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
    objects = QueueManager()

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
            project_permissions__project=self.sector.project,
            project_permissions__queue_authorizations__queue=self,
        )

    @property
    def online_agents(self):
        # Filtra agentes online
        agents = self.agents.filter(
            project_permissions__status="ONLINE",
            project_permissions__project=self.sector.project,
            project_permissions__queue_authorizations__queue=self,
            project_permissions__queue_authorizations__role=1,
        )

        # remove agents that have active custom status other than in service
        return agents.exclude(
            models.Q(
                user_custom_status__is_active=True,
                user_custom_status__project=self.sector.project,
            )
            & ~models.Q(user_custom_status__status_type__name__iexact="In-service")
        )  # TODO: Set this variable to ProjectPermission.STATUS_ONLINE

    @property
    def available_agents(self):
        routing_option = self.project.routing_option
        rooms_active_filter = models.Q(rooms__is_active=True)
        rooms_sector_filter = models.Q(rooms__queue__sector=self.sector)

        rooms_count_filter = models.Q(rooms_active_filter & rooms_sector_filter)
        online_agents = self.online_agents.annotate(
            active_rooms_count=models.Count(
                "rooms",
                filter=rooms_count_filter,
            )
        ).filter(active_rooms_count__lt=self.limit)

        if routing_option == "general":
            rooms_day_closed_filter = models.Q(
                rooms__ended_at__date__gte=timezone.now().date()
            )
            rooms_active_or_day_closed_filter = (
                rooms_active_filter | rooms_day_closed_filter
            )
            rooms_sector_and_active_or_day_closed_filter = (
                rooms_sector_filter & rooms_active_or_day_closed_filter
            )

            online_agents = online_agents.annotate(
                active_and_day_closed_rooms=models.Count(
                    "rooms", filter=rooms_sector_and_active_or_day_closed_filter
                )
            )

            return online_agents.order_by("active_and_day_closed_rooms")

        return online_agents.order_by("active_rooms_count")

    def get_available_agent(self):
        """
        Get an available agent for a queue, based on the number of active rooms.

        If the active rooms count is the same for different agents,
        a random agent, among the ones with the rooms count, is returned.
        """
        agents = list(self.available_agents)

        if not agents:
            return None

        routing_option = self.sector.project.routing_option
        field_name = (
            "active_and_day_closed_rooms"
            if routing_option == "general"
            else "active_rooms_count"
        )

        min_rooms_count = min(getattr(agent, field_name) for agent in agents)

        eligible_agents = [
            agent for agent in agents if getattr(agent, field_name) == min_rooms_count
        ]

        return random.choice(eligible_agents)

    def is_agent(self, user):
        return self.authorizations.filter(permission__user=user).exists()

    def get_or_create_user_authorization(self, user):
        queue_auth, created = self.authorizations.get_or_create(permission__user=user)
        return queue_auth

    def set_queue_authorization(self, user, role: int):
        queue_auth, created = self.authorizations.get_or_create(
            permission__user=user, role=role
        )
        return queue_auth

    def set_user_authorization(self, permission, role: int):
        queue_auth, created = self.authorizations.get_or_create(
            permission=permission, role=role
        )
        return queue_auth

    @property
    def project(self):
        return self.sector.project


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
    def project(self):
        return self.queue.project

    @property
    def is_agent(self):
        return self.role == self.ROLE_AGENT

    @property
    def user(self):
        return self.permission.user

    @property
    def can_list(self):
        return self.is_agent
