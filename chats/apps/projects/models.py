from builtins import property
from django.db import models
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField
from chats.core.models import BaseModel

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
            return self.authorizations.get(user=user)
        except ProjectPermission.DoesNotExist:
            return None

    def get_sectors(self, user):
        user_permission = self.get_permission(user)
        if user_permission is not None and user_permission.role == 1:  # Admin role
            return self.sectors.all()
        else:
            return self.sectors.filter(
                authorizations__user=user
            )  # If the user have any permission on the sectors


class ProjectPermission(BaseModel):
    ROLE_USER = 0
    ROLE_ADMIN = 1
    ROLE_EXTERNAL = 2

    ROLE_CHOICES = [
        (ROLE_USER, _("user")),
        (ROLE_ADMIN, _("admin")),
        (ROLE_EXTERNAL, _("external")),
    ]

    project = models.ForeignKey(
        Project,
        verbose_name=_("Project"),
        related_name="authorizations",
        to_field="uuid",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("users"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_USER
    )

    class Meta:
        verbose_name = _("Project Permission")
        verbose_name_plural = _("Project Permissions")

    def __str__(self):
        return self.project.name

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_external(self):
        return self.role == self.ROLE_EXTERNAL

    @property
    def can_edit(self):
        return self.is_admin
