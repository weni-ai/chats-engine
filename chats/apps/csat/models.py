from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from model_utils import FieldTracker
from django.db import transaction

from chats.core.models import BaseModel


CSAT_FLOW_CACHE_KEY = "csat_flow_uuid:{project_uuid}"
CSAT_FLOW_CACHE_TTL = 300  # 5 minutes


class CSATSurvey(BaseModel):
    room = models.OneToOneField(
        "rooms.Room",
        verbose_name=_("Room"),
        on_delete=models.CASCADE,
        related_name="csat_survey",
    )
    rating = models.PositiveSmallIntegerField(
        _("Rating"), validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(_("Comment"), blank=True, null=True)
    answered_on = models.DateTimeField(_("Answered on"))

    class Meta:
        verbose_name = _("CSAT Survey")
        verbose_name_plural = _("CSAT Surveys")

    def __str__(self):
        return f"{self.room.uuid} - {self.rating}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CSATFlowProjectConfig(BaseModel):
    project = models.OneToOneField(
        "projects.Project",
        verbose_name=_("Project"),
        on_delete=models.CASCADE,
        related_name="csat_flow_project_config",
    )
    flow_uuid = models.UUIDField(_("Flow UUID"))
    version = models.IntegerField(_("Version"))

    tracker = FieldTracker(fields=["flow_uuid"])

    class Meta:
        verbose_name = _("CSAT Flow Project Config")
        verbose_name_plural = _("CSAT Flow Project Configs")

    def __str__(self):
        return f"{self.project.name} - {self.flow_uuid}"

    def invalidate_flow_uuid_cache(self):
        from chats.core.cache import CacheClient

        cache_client = CacheClient()
        cache_key = CSAT_FLOW_CACHE_KEY.format(project_uuid=str(self.project.uuid))
        cache_client.delete(cache_key)

    def save(self, *args, **kwargs):
        flow_uuid_has_changed = self.tracker.has_changed("flow_uuid")

        super().save(*args, **kwargs)

        if flow_uuid_has_changed:
            transaction.on_commit(lambda: self.invalidate_flow_uuid_cache())
