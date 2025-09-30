from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from chats.core.models import BaseModel


class CSATSurvey(BaseModel):
    room = models.OneToOneField(
        "rooms.Room",
        verbose_name=_("Room"),
        on_delete=models.CASCADE,
        related_name="csat_survey",
    )
    score = models.PositiveSmallIntegerField(
        _("Score"), validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(_("Comment"), blank=True, null=True)
    answered_on = models.DateTimeField(_("Answered on"))

    class Meta:
        verbose_name = _("CSAT Survey")
        verbose_name_plural = _("CSAT Surveys")

    def __str__(self):
        return f"{self.room.uuid} - {self.score}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
