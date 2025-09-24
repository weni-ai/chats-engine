from django.db import models


class SoftDeletableManager(models.Manager):
    """
    Manager for soft deletable models.
    """

    def __init__(self, *args, include_deleted: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_deleted = include_deleted

    def get_queryset(self):
        if self.include_deleted:
            return super().get_queryset()

        return super().get_queryset().filter(is_deleted=False)
