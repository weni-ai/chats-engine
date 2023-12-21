from django.db import models


class UserPermissionsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(user__isnull=False)


class ExternalAuthManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(user__isnull=True)
