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
    message_response_time = models.IntegerField(_("Messages response time"), default=0)
    interaction_time = models.IntegerField(_("Room interaction time"), default=0)
    transfer_count = models.IntegerField(_("Room transfer count"), default=0)

    class Meta:
        verbose_name = _("Room Metric")
        verbose_name_plural = _("Rooms Metrics")

    def __str__(self):
        return self.room.queue.name

    @property
    def project(self):
        return self.room.project


class ReportStatus(BaseModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    fields_config = models.JSONField()
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Report Status: {self.project.name} - {self.status}"