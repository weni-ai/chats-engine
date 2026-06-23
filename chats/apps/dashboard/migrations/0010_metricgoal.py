import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0009_reportstatus_report_type_reportstatus_room"),
        ("projects", "0038_project_is_chats_summary_enabled"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetricGoal",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(
                        auto_now_add=True, editable=False, verbose_name="Created on"
                    ),
                ),
                (
                    "modified_on",
                    models.DateTimeField(auto_now=True, verbose_name="Modified on"),
                ),
                (
                    "metric",
                    models.CharField(
                        choices=[
                            ("waiting_time", "Waiting time"),
                            ("first_response_time", "First response time"),
                            (
                                "conversation_duration",
                                "Conversation duration",
                            ),
                        ],
                        max_length=50,
                        verbose_name="Metric",
                    ),
                ),
                (
                    "threshold_seconds",
                    models.PositiveIntegerField(verbose_name="Threshold in seconds"),
                ),
                (
                    "unit",
                    models.CharField(
                        choices=[
                            ("s", "Seconds"),
                            ("m", "Minutes"),
                            ("h", "Hours"),
                        ],
                        default="s",
                        max_length=1,
                        verbose_name="Unit",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is active"),
                ),
                (
                    "email_enabled",
                    models.BooleanField(default=False, verbose_name="Email enabled"),
                ),
                (
                    "rooms_threshold_count",
                    models.PositiveIntegerField(
                        default=5, verbose_name="Rooms threshold count"
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metric_goals",
                        to="projects.project",
                        verbose_name="Project",
                    ),
                ),
                (
                    "recipients",
                    models.ManyToManyField(
                        blank=True,
                        related_name="metric_goal_notifications",
                        to="projects.projectpermission",
                        verbose_name="Recipients",
                    ),
                ),
            ],
            options={
                "verbose_name": "Metric goal",
                "verbose_name_plural": "Metric goals",
            },
        ),
        migrations.AddConstraint(
            model_name="metricgoal",
            constraint=models.UniqueConstraint(
                fields=("project", "metric"),
                name="unique_project_metric_goal",
            ),
        ),
    ]
