from django.db import models
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField
from chats.core.models import BaseModel

from django.core.exceptions import ObjectDoesNotExist

from chats.utils.websockets import send_channels_group
from chats.apps.api.v1.internal.rest_clients.connect_rest_client import (
    ConnectRESTClient,
)

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
    flows_authorization = models.CharField(
        _("Flows Authorization Token"), max_length=50, null=True, blank=True
    )
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

    def set_flows_project_auth_token(self, user_email: str = ""):
        email = user_email or self.random_admin.user.email
        response = ConnectRESTClient().get_user_project_token(self, email)
        token = response.json().get("api_token")
        self.flows_authorization = token
        self.save()
        return token

    @property
    def random_admin(self):
        return self.permissions.filter(role=ProjectPermission.ROLE_ADMIN).first()

    def get_sectors(self, user, custom_filters: dict = {}):
        user_permission = self.get_permission(user)
        sectors = self.sectors.all()
        if (
            user_permission is not None
            and user_permission.role == ProjectPermission.ROLE_ADMIN
        ):  # Admin role
            return sectors

        return sectors.filter(authorizations__permission=user_permission)


class ProjectPermission(
    BaseModel
):  # TODO: ADD CONSTRAINT NOT TO SAVE THE SAME USER 2 TIME IN THE PROJECT
    ROLE_NOT_SETTED = 0
    ROLE_ADMIN = 1
    ROLE_ATTENDANT = 2

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_ADMIN, _("admin")),
        (ROLE_ATTENDANT, _("Attendant")),
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
        _("User Status"), max_length=10, choices=STATUS_CHOICES, default=STATUS_OFFLINE
    )

    first_access = models.BooleanField(
        _("Is it the first access of user?"), default=True
    )

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

    def notify_user(self, action, sender="user"):
        """ """
        send_channels_group(
            group_name=f"permission_{self.pk}",
            call_type="notify",
            content={"from": sender, "status": self.status},
            action=f"status.{action}",
        )

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
        if self.role == self.ROLE_ATTENDANT:
            limits = (
                self.queue_authorizations.all()
                .distinct("queue__sector")
                .values_list("queue__sector__limit", flat=True)
            )
            return max(limits)
        return 0  # If the user is not an agent, it won't be possible to receive rooms automatically


class LinkContact(BaseModel):
    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("User"),
        related_name="linked_contacts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        verbose_name=_("Contact"),
        related_name="linked_users",
        on_delete=models.CASCADE,
    )
    project = models.ForeignKey(
        Project,
        verbose_name=_("project"),
        related_name="linked_contacts",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Linked Contact")
        verbose_name_plural = _("Linked Contacts")
        constraints = [
            models.UniqueConstraint(
                fields=["contact", "project"], name="unique_link_contact_per_project"
            )
        ]

    def __str__(self):
        return self.project.name

    @property
    def full_name(self):
        if self.user:
            return self.user.full_name
        else:
            return ""

    @property
    def is_online(self):
        try:
            perm = self.project.permissions.get(user=self.user)
            return perm.status.lower() == "online"
        except (AttributeError, ProjectPermission.DoesNotExist):
            return False


class FlowStart(BaseModel):
    external_id = models.CharField(
        _("External ID"), max_length=200, blank=True, null=True
    )
    flow = models.CharField(_("flow ID"), max_length=200, blank=True, null=True)
    project = models.ForeignKey(
        Project,
        verbose_name=_("Project"),
        related_name="flowstarts",
        on_delete=models.CASCADE,
    )
    permission = models.ForeignKey(
        ProjectPermission,
        verbose_name=_("Permission"),
        related_name="flowstarts",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Flow Start")
        verbose_name_plural = _("Flow Starts")

    def __str__(self):
        return self.project.name


class ContactGroupFlowReference(BaseModel):
    receiver_type = models.CharField(_("Receiver Type"), max_length=50)
    external_id = models.CharField(
        _("External ID"), max_length=200, blank=True, null=True
    )
    flow_start = models.ForeignKey(
        FlowStart,
        verbose_name=_("Flow Start"),
        related_name="references",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Flow contact/group Reference")
        verbose_name_plural = _("Flow contact/group References")

    def __str__(self):
        return self.flow_start.project.name
