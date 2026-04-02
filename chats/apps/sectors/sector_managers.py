from django.db import models

from chats.core.managers import SoftDeletableManager


class SectorManager(SoftDeletableManager):
    pass


class SectorAuthorizationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(permission__is_deleted=False)
