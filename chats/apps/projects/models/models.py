from django.contrib.auth import get_user_model
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import IntegrityError, models, transaction
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _
from requests.exceptions import JSONDecodeError
from timezone_field import TimeZoneField

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.internal.rest_clients.integrations_rest_client import (
    IntegrationsRESTClient,
)
from chats.core.models import BaseConfigurableModel, BaseModel, BaseSoftDeleteModel
from chats.utils.websockets import send_channels_group

from .permission_managers import UserPermissionsManager

User = get_user_model()

# Create your models here.


class TemplateType(BaseSoftDeleteModel, BaseModel):
    name = models.CharField(max_length=255)
    setup = models.JSONField(_("Template Setup"), default=dict)

    def __str__(self) -> str:
        return self.name  # pragma: no cover

    class Meta:
        verbose_name = "TemplateType"
        verbose_name_plural = "TemplateTypes"


class Project(BaseConfigurableModel, BaseModel):
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
    is_template = models.BooleanField(_("is template?"), default=False)
    template_type = models.ForeignKey(
        TemplateType,
        verbose_name=_("template type"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    org = models.CharField(_("org uuid"), max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return self.name

    @property
    def agents_can_see_queue_history(self):
        """
        True > agents will see the whole history of the queues they have permission in
        False > agents will only see rooms that have been closed by them
        """
        try:
            return self.config.get("agents_can_see_queue_history", True)
        except AttributeError:
            return True

    @property
    def routing_option(self):
        """
        OPTIONS>
            "general": will consider closed rooms on the day. e.g.: a agent has 3 open rooms and 1 closed,
                the limit for the sector is 4, new rooms will go to other agents or stay in the queue.
            None: Will only consider open rooms, does not matter when the room was created.
        """
        try:
            return self.config.get("routing_option", None)
        except AttributeError:
            return None

    @property
    def history_contacts_blocklist(self):
        try:
            return self.config.get("history_contacts_blocklist", [])
        except AttributeError:
            return []

    @property
    def openai_token(self):
        try:
            return self.config.get("openai_token")
        except AttributeError:
            return None

    @property
    def external_token(self):
        try:
            return self.permissions(manager="auth").get_or_create(user=None, role=1)[0]
        except MultipleObjectsReturned:
            return self.permissions(manager="auth").filter(user=None, role=1).first()

    def add_contact_to_history_blocklist(self, contact_external_id: str):
        config = self.config or {}
        blocked_list = self.history_contacts_blocklist
        blocked_list.append(contact_external_id)
        config["history_contacts_blocklist"] = blocked_list
        self.config = config
        self.save()

    def get_permission(self, user):
        try:
            return self.permissions.get(user=user)
        except ProjectPermission.DoesNotExist:
            return None

    def set_flows_project_auth_token(
        self, user_email: str = "", permissions: list = []
    ):
        if user_email != "":
            permissions.insert(0, user_email)
        while permissions != []:
            email = permissions.pop(0)
            response = FlowRESTClient().get_user_api_token(str(self.uuid), email)
            if response.status_code == 200:
                break
        try:
            token = response.json().get("api_token")
        except (UnboundLocalError, JSONDecodeError):
            return None
        self.flows_authorization = token
        self.save()
        return token

    def set_chat_gpt_auth_token(self, user_login_token: str = ""):
        token = IntegrationsRESTClient().get_chatgpt_token(
            str(self.pk), user_login_token
        )
        config = self.config or {}
        config["chat_gpt_token"] = token
        self.config = config
        self.save()
        return token

    def get_openai_token(self, user_login_token):
        token = self.openai_token
        if token:
            return token
        return self.set_chat_gpt_auth_token(user_login_token)

    @property
    def admin_permissions(self):
        return self.permissions.filter(role=ProjectPermission.ROLE_ADMIN)

    @property
    def random_admin(self):
        return self.admin_permissions.first()

    @property
    def admins(self):
        return User.objects.filter(
            project_permissions__project=self, project_permissions__role=1
        )

    @property
    def online_admins(self):
        return User.objects.filter(
            project_permissions__project=self,
            project_permissions__role=1,
            project_permissions__status="ONLINE",
        )

    def get_sectors(self, user, custom_filters: dict = {}):
        user_permission = self.get_permission(user)
        sectors = self.sectors.all()
        if (
            user_permission is not None
            and user_permission.role == ProjectPermission.ROLE_ADMIN
        ):  # Admin role
            return sectors
        sector_auth_filter = Q(authorizations__permission=user_permission)
        queue_auth_filter = Q(queues__authorizations__permission=user_permission)
        return sectors.filter(
            Q(sector_auth_filter | queue_auth_filter), **custom_filters
        ).distinct()


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

    objects = UserPermissionsManager()
    auth = models.Manager()

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

    def get_sectors(self, custom_filters: dict = {}):
        sectors = self.project.sectors.all()
        if self.role == ProjectPermission.ROLE_ADMIN:  # Admin role
            return sectors
        sector_auth_filter = Q(authorizations__permission=self)
        queue_auth_filter = Q(queues__authorizations__permission=self)
        return sectors.filter(
            Q(sector_auth_filter | queue_auth_filter), **custom_filters
        ).distinct()

    def notify_user(self, action, sender="user"):
        """ """
        send_channels_group(
            group_name=f"permission_{self.pk}",
            call_type="notify",
            content={"from": sender, "status": self.status},
            action=f"status.{action}",
        )

    def manager_sectors(self, custom_filters: dict = {}):
        sectors = self.project.sectors.all()
        if self.role == ProjectPermission.ROLE_ADMIN:  # Admin role
            return sectors
        sector_auth_filter = Q(authorizations__permission=self)
        return sectors.filter(sector_auth_filter).distinct()

    @property
    def is_user(self):
        return self.role == self.ROLE_USER

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_manager(
        self, sector: str = None, queue: str = None, any_sector: bool = False
    ):
        if self.is_admin:
            return True
        if any_sector is True:
            return self.sector_authorizations.exists()
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

    def is_agent(self, queue: str, any_queue: bool = False, sector: str = None) -> bool:
        if self.is_admin:
            return True
        if any_queue:
            return self.queue_authorizations.exists()
        if sector:
            return (
                self.sector_authorizations.filter(sector=sector).exists()
                or self.queue_authorizations.filter(queue__sector=sector).exists()
            )
        if queue is None:
            return False

        sector = self.project.sectors.get(queues=queue)

        if self.is_manager(sector=str(sector.uuid)):
            return True
        self.queue_authorizations.get(queue__uuid=queue)
        return True  # 1 = agent role at QueueAuthorization

    def is_agent_on_sector(self, sector: str) -> bool:
        if self.is_admin:
            return True
        return self.sector_authorization

    # TODO: remove soft deleted queues/sectors
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
            .exclude(role=2)
            .values_list("queue", flat=True)
        )
        queues = set(sector_manager_queues + queue_agent_queues)

        return queues

    def get_permission(self, user):
        try:
            return self.project.get_permission(user=user)
        except ObjectDoesNotExist:
            return None

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
    name = models.TextField(_("flow name"), blank=True, null=True, default="")
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
        on_delete=models.SET_NULL,
        null=True,
    )
    room = models.ForeignKey(
        "rooms.Room",
        verbose_name=_("room"),
        related_name="flowstarts",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_deleted = models.BooleanField(_("is deleted?"), default=False)
    contact_data = models.JSONField(_("contact data"), default=dict)

    class Meta:
        verbose_name = _("Flow Start")
        verbose_name_plural = _("Flow Starts")

    def __str__(self):
        return self.project.name


class ContactGroupFlowReference(BaseModel):
    receiver_type = models.CharField(
        _("Receiver Type"), max_length=50
    )  # Contact or Group, may use choices in the future
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
        return self.receiver_type + ": " + self.external_id

    @property
    def project(self):
        return self.flow_start.project


class CustomStatusType(BaseModel, BaseConfigurableModel):
    name = models.CharField(max_length=255)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="custom_statuses"
    )
    is_deleted = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])

    def save(self, *args, **kwargs):
        if not self.pk:
            with transaction.atomic():
                existing_count = (
                    CustomStatusType.objects.select_for_update()
                    .filter(project=self.project, is_deleted=False, config__created_by_system__isnull=True)
                    .count()
                )
                if existing_count > 10:
                    raise ValidationError(
                        "A project can have a maximum of 10 custom statuses."
                    )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_permission(self, user):
        try:
            return self.project.permissions.get(user=user)
        except ProjectPermission.DoesNotExist:
            return None

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name", "project"],
                condition=Q(is_deleted=False),
                name="unique_custom_status",
            )
        ]


class CustomStatus(BaseModel):
    user = models.ForeignKey(
        "accounts.User",
        related_name="user_custom_status",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    status_type = models.ForeignKey(
        "CustomStatusType", on_delete=models.CASCADE, to_field="uuid"
    )
    is_active = models.BooleanField(default=True)
    break_time = models.PositiveIntegerField(_("Custom status timming"), default=0)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                condition=models.Q(is_active=True),
                name="unique_active_custom_status_per_user_project",
            )
        ]

    def save(self, *args, **kwargs):
        if self.status_type:
            self.project = self.status_type.project

        try:
            with transaction.atomic():
                if self.is_active and self.user:
                    CustomStatus.objects.filter(
                        user=self.user, project=self.project, is_active=True
                    ).exclude(pk=self.pk).update(is_active=False)

                super().save(*args, **kwargs)
        except IntegrityError as error:
            if "unique_active_custom_status_per_user_project" in str(error):
                raise ValidationError(
                    "you can't have more than one active status per project."
                )
            raise
