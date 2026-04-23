from django.db import models

from chats.core.managers import SoftDeletableManager


class QueueManager(SoftDeletableManager):
    pass


class QueueAuthorizationManager(models.Manager):
    def __init__(self, *args, include_deleted: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_deleted = include_deleted

    def get_queryset(self):
        if self.include_deleted:
            return super().get_queryset()

        return super().get_queryset().filter(permission__is_deleted=False)
