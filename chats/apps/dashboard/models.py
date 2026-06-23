from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
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
    first_response_time = models.IntegerField(
        _("First response time"), null=True, blank=True, default=None
    )
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
    MAX_RETRY_COUNT = 3

    REPORT_TYPE_CUSTOM_DASHBOARD = "custom_dashboard"
    REPORT_TYPE_ROOM_EXPORT = "room_export"
    REPORT_TYPE_CHOICES = [
        (REPORT_TYPE_CUSTOM_DASHBOARD, "Custom Dashboard"),
        (REPORT_TYPE_ROOM_EXPORT, "Room Export"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="export_reports",
    )
    report_type = models.CharField(
        max_length=30,
        choices=REPORT_TYPE_CHOICES,
        default=REPORT_TYPE_CUSTOM_DASHBOARD,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
            ("failed", "Failed"),
            ("permanently_failed", "Permanently Failed"),
        ],
        default="pending",
    )
    fields_config = models.JSONField()
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Report Status: {self.project.name} - {self.status}"


class MetricGoal(BaseModel):
    METRIC_WAITING_TIME = "waiting_time"
    METRIC_FIRST_RESPONSE_TIME = "first_response_time"
    METRIC_CONVERSATION_DURATION = "conversation_duration"

    METRIC_CHOICES = [
        (METRIC_WAITING_TIME, _("Waiting time")),
        (METRIC_FIRST_RESPONSE_TIME, _("First response time")),
        (METRIC_CONVERSATION_DURATION, _("Conversation duration")),
    ]

    UNIT_SECOND = "s"
    UNIT_MINUTE = "m"
    UNIT_HOUR = "h"

    UNIT_CHOICES = [
        (UNIT_SECOND, _("Seconds")),
        (UNIT_MINUTE, _("Minutes")),
        (UNIT_HOUR, _("Hours")),
    ]

    DEFAULT_ROOMS_THRESHOLD_COUNT = 5

    project = models.ForeignKey(
        "projects.Project",
        related_name="metric_goals",
        verbose_name=_("Project"),
        on_delete=models.CASCADE,
    )
    metric = models.CharField(_("Metric"), max_length=50, choices=METRIC_CHOICES)
    threshold_seconds = models.PositiveIntegerField(_("Threshold in seconds"))
    unit = models.CharField(
        _("Unit"),
        max_length=1,
        choices=UNIT_CHOICES,
        default=UNIT_SECOND,
    )
    is_active = models.BooleanField(_("Is active"), default=True)
    email_enabled = models.BooleanField(_("Email enabled"), default=False)
    rooms_threshold_count = models.PositiveIntegerField(
        _("Rooms threshold count"),
        default=DEFAULT_ROOMS_THRESHOLD_COUNT,
    )
    rooms_threshold_percent = models.PositiveSmallIntegerField(
        _("Rooms threshold percent"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_(
            "When set, takes precedence over rooms_threshold_count and "
            "represents the percentage of active rooms in violation "
            "required to trigger the alert."
        ),
    )
    recipients = models.ManyToManyField(
        "projects.ProjectPermission",
        related_name="metric_goal_notifications",
        verbose_name=_("Recipients"),
        blank=True,
    )

    class Meta:
        verbose_name = _("Metric goal")
        verbose_name_plural = _("Metric goals")
        constraints = [
            models.UniqueConstraint(
                fields=["project", "metric"],
                name="unique_project_metric_goal",
            )
        ]
        indexes = [
            models.Index(
                fields=["metric", "project"],
                name="metric_goal_active_lookup_idx",
                condition=Q(is_active=True),
            ),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.metric}"
