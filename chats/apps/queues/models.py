import random

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from chats.apps.projects.models.models import CustomStatus
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
    all_objects = QueueManager(include_deleted=True)

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
        group_sector = self.sector.group_sectors.filter(is_deleted=False).first()
        if group_sector:
            return group_sector.rooms_limit
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

        custom_status_query = Subquery(
            CustomStatus.objects.filter(
                Q(user__id=OuterRef("id"))
                & Q(is_active=True)
                & Q(status_type__project=self.sector.project)
                & ~Q(status_type__name__iexact="in-service")
            ).values("user__id")
        )

        return agents.exclude(
            id__in=custom_status_query
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

    def _get_agent_with_least_rooms_closed_today(self, agents):
        """
        Returns the agent that closed the fewest rooms today.
        If there is a tie, returns a random agent.
        """
        from datetime import timedelta

        from chats.apps.rooms.models import Room

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        rooms_closed_counts = (
            Room.objects.filter(
                user__in=agents,
                queue__sector=self.sector,
                ended_at__gte=today_start,
                ended_at__lt=tomorrow_start,
                is_active=False,
            )
            .values("user_id")
            .annotate(count=models.Count("uuid"))
        )

        # user_id is the email (to_field="email" in Room.user ForeignKey)
        rooms_closed_today = {item["user_id"]: item["count"] for item in rooms_closed_counts}
        min_closed_today = min(rooms_closed_today.get(agent.email, 0) for agent in agents)

        eligible_agents = [agent for agent in agents if rooms_closed_today.get(agent.email, 0) == min_closed_today]

        return random.choice(eligible_agents)

    def get_available_agent(self):
        """
        Get an available agent for a queue, based on the number of active rooms.

        If the active rooms count is the same for different agents,
        the agent with the least rooms closed today is selected.
        If there is still a tie, a random agent is returned.
        """
        agents = list(self.available_agents)
        print('agents', agents)
        if not agents:
            return None

        routing_option = self.sector.project.routing_option
        field_name = (
            "active_and_day_closed_rooms"
            if routing_option == "general"
            else "active_rooms_count"
        )

        min_rooms_count = min(getattr(agent, field_name) for agent in agents)
        print('min_rooms_count', min_rooms_count)
        eligible_agents = [
            agent for agent in agents if getattr(agent, field_name) == min_rooms_count
        ]
        print('eligible_agents', eligible_agents)
        if len(eligible_agents) == 1:
            print('verificando se tem agente')
            return eligible_agents[0]

        print('chamando _get_agent_with_least_rooms_closed_today')
        return self._get_agent_with_least_rooms_closed_today(eligible_agents)

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

    @property
    def required_tags(self) -> bool:
        return self.sector.required_tags


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
