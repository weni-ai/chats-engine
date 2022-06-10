from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Project(models.Model):

    name = models.CharField(_("name"), max_length=50)
    connect_pk = models.CharField(
        _("Connect ID"), max_length=150, null=True, blank=True
    )

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return self.name


class ProjectPermission(models.Model):
    ROLE_NOT_SETTED = 0
    ROLE_ADMIN = 1

    ROLE_CHOICES = [
        (ROLE_NOT_SETTED, _("not set")),
        (ROLE_ADMIN, _("admin")),
    ]

    project = models.ForeignKey(
        Project, verbose_name=_("Project"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        "accounts.User", verbose_name=_("users"), on_delete=models.CASCADE
    )
    role = models.PositiveIntegerField(
        _("role"), choices=ROLE_CHOICES, default=ROLE_NOT_SETTED
    )

    class Meta:
        verbose_name = _("Project Permission")
        verbose_name_plural = _("Project Permissions")

    def __str__(self):
        return self.name
