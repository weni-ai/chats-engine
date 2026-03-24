from django.db import models

from chats.core.managers import SoftDeletableManager


class UserPermissionsManager(SoftDeletableManager):
    def get_queryset(self):
        return super().get_queryset().filter(user__isnull=False)
