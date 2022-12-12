from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class RoomMetrics(BaseModel):
    room = models.OneToOneField(
        "rooms.Room",
        related_name="metric",
        verbose_name=_("Room Metric"),
        on_delete=models.CASCADE,
    )
    waiting_time = models.IntegerField(_("Room Waiting time"), default=0)
    queued_count = models.IntegerField(_("Queued count"), default=0)
    message_response_time =  models.IntegerField(_("Messages response time"), default=0)
    interaction_time = models.IntegerField(_("Room interaction time"), default=0)