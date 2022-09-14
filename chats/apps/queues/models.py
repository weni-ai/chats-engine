from django.db import models
from chats.core.models import BaseModel
from django.utils.translation import gettext_lazy as _


class Queue(BaseModel):
    sector = models.ForeignKey(
        "sectors.Sector",
        verbose_name=_("sector"),
        related_name="queues",
        on_delete=models.CASCADE,
    )
    name = models.CharField(_("Name"), max_length=150, blank=True)

    class Meta:
        verbose_name = _("Sector Queue")
        verbose_name_plural = _("Sector Queues")

    def __str__(self):
        return self.name

    @property
    def queue(self):
        return self

    @property
    def limit(self):
        return self.sector.limit

    def get_permission(self, user):
        return self.sector.get_permission(user=user)

    @property
    def agent_count(self):
        return self.authorizations.filter(role=QueueAuthorization.ROLE_AGENT).count()

    def get_or_create_user_authorization(self, user):
        sector_auth, created = self.authorizations.get_or_create(user=user)
        return sector_auth

    def set_queue_authorization(self, user, role: int):
        sector_auth, created = self.authorizations.get_or_create(user=user, role=role)
        return sector_auth

    @property
    def available_agents(self):
        project = self.sector.project
        qauth = self.authorizations.annotate(
            limit=models.Max(
                "permission__queue_authorizations__queue__sector__rooms_limit"
            )
        )
        qauth = qauth.annotate(
            rooms=models.Count(
                "permission__user__rooms",
                filter=models.Q(
                    permission__user__rooms__queue__sector__project=project
                ),
                distinct=True,
            )
        )  # TODO: CHECK IF IT WILL RETURN ROOMS FROM OTHER PROJECTS THAT THE USER HAS PERMISSION TO

        return qauth.filter(permission__status="online", limit__gt=models.F("rooms"))


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

    def __str__(self):
        return self.get_role_display()

    def get_permission(self, user):
        return self.queue.get_permission(user)

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
