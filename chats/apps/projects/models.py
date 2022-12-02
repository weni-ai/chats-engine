from django.db import models
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField
from chats.core.models import BaseModel

from django.core.exceptions import ObjectDoesNotExist

# Create your models here.


class Project(BaseModel):

    DATE_FORMAT_DAY_FIRST = "D"
    DATE_FORMAT_MONTH_FIRST = "M"
    DATE_FORMATS = (
        (DATE_FORMAT_DAY_FIRST, "DD-MM-YYYY"),
        (DATE_FORMAT_MONTH_FIRST, "MM-DD-YYYY"),
    )

    name = models.CharField(_("name"), max_length=50)
    timezone = TimeZoneField(verbose_name=_("Timezone"))
    date_format = models.CharField(
        verbose_name=_("Date Format"),
        max_length=1,
        choices=DATE_FORMATS,
        default=DATE_FORMAT_DAY_FIRST,
        help_text=_("Whether day comes first or month comes first in dates"),
    )

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return self.name

    def get_permission(self, user):
        try:
            return self.permissions.get(user=user)
        except ProjectPermission.DoesNotExist:
            return None

    def get_sectors(self, user):
        user_permission = self.get_permission(user)
        if user_permission is not None and user_permission.role == 1:  # Admin role
            return self.sectors.all()
        else:
            return self.sectors.filter(
                authorizations__permission=user_permission
            )  # If the user have any permission on the sectors


class ProjectPermission(
    BaseModel
):  # TODO: ADD CONSTRAINT NOT TO SAVE THE SAME USER 2 TIME IN THE PROJECT
    ROLE_NOT_SETTED = 0
    ROLE_ADMIN = 1
    ROLE_AGENT = 2
    ROLE_SERVICE_MANAGER = 3

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_ADMIN, _("admin")),
        (ROLE_AGENT, _("agent")),
        (ROLE_SERVICE_MANAGER, _("service manager")),
    ]

    STATUS_ONLINE = "ONLINE"
    STATUS_OFFLINE = "OFFLINE"
    STATUS_AWAY = "AWAY"
    STATUS_BUSY = "BUSY"

    STATUS_CHOICES = [
        (STATUS_ONLINE, _("online")),
        (STATUS_OFFLINE, _("offline")),
        (STATUS_AWAY, _("away")),
        (STATUS_BUSY, _("busy")),
    ]

    project = models.ForeignKey(
        Project,
        verbose_name=_("Project"),
        related_name="permissions",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="project_permissions",
        verbose_name=_("users"),
        on_delete=models.CASCADE,
        to_field="email",
        null=True,
        blank=True,
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_NOT_SETTED
    )

    status = models.CharField(
        _("User Status"), max_length=10, choices=ROLE_CHOICES, default=STATUS_OFFLINE
    )

    first_access = models.BooleanField(_("Its the first access of user?"), default=True)

    class Meta:
        verbose_name = _("Project Permission")
        verbose_name_plural = _("Project Permissions")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"], name="unique_user_permission"
            )
        ]

    def __str__(self):
        return self.project.name

    @property
    def is_user(self):
        return self.role == self.ROLE_USER

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_manager(self, sector: str = None, queue: str = None):
        if self.is_admin:
            return True
        qs = (
            models.Q(sector__uuid=sector)
            if sector is not None
            else models.Q(sector__queues__uuid=queue)
        )
        try:
            sector_authorization = self.sector_authorizations.get(qs)
            return (
                sector_authorization.role == 1
            )  # 1 = manager role at SectorAuthorization
        except ObjectDoesNotExist:
            pass

        return False

    def is_agent(self, queue: str):
        if queue is None:
            return False
        sector = self.project.sectors.get(queues__uuid=queue)

        if self.is_manager(sector=str(sector.uuid)):
            return True
        queue_authorization = self.queue_authorizations.get(queue__uuid=queue)
        return queue_authorization.role == 1  # 1 = agent role at QueueAuthorization

    @property
    def queue_ids(self):
        if self.is_admin:
            return list(
                self.project.sectors.filter(queues__isnull=False)
                .values_list("queues__uuid", flat=True)
                .distinct()
            )
        sector_manager_queues = list(
            self.sector_authorizations.filter(sector__queues__isnull=False)
            .values_list("sector__queues__uuid", flat=True)
            .distinct()
        )
        queue_agent_queues = list(
            self.queue_authorizations.exclude(queue__uuid__in=sector_manager_queues)
            .values_list("queue", flat=True)
            .distinct()
        )
        queues = set(sector_manager_queues + queue_agent_queues)

        return queues

    def get_permission(self, user):
        return self.project.get_permission(user=user)

    @property
    def rooms_limit(self):
        if self.role == self.ROLE_AGENT:
            limits = (
                self.queue_authorizations.all()
                .distinct("queue__sector")
                .values_list("queue__sector__limit", flat=True)
            )
            return max(limits)
        return 0  # If the user is not an agent, it won't be possible to receive rooms automatically
