import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_on = models.DateTimeField(
        _("Created on"), editable=False, auto_now_add=True
    )
    modified_on = models.DateTimeField(_("Modified on"), auto_now=True)

    class Meta:
        abstract = True

    @property
    def edited(self) -> bool:
        return bool(self.modified_by)
