import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    created_on = models.DateTimeField(
        _("Created on"), editable=False, auto_now_add=True
    )
    modified_on = models.DateTimeField(_("Modified on"), auto_now=True)

    class Meta:
        abstract = True

    @property
    def edited(self) -> bool:
        return bool(self.modified_by)


class BaseSoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(_("is deleted?"), default=False)

    class Meta:
        abstract = True

    def deleted_sufix(self):
        name_sufix = "_is_deleted_" + str(timezone.now())
        return name_sufix

    def delete(self):
        self.is_deleted = True
        self.name += self.deleted_sufix()
        self.save()
