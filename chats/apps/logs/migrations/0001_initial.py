# Generated manually for chats.apps.logs

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Log",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created on"),
                ),
                (
                    "modified_on",
                    models.DateTimeField(auto_now=True, verbose_name="Modified on"),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("CREATE", "Create"),
                            ("UPDATE", "Update"),
                            ("DELETE", "Delete"),
                        ],
                        max_length=10,
                        verbose_name="Action",
                    ),
                ),
                ("object_id", models.UUIDField(verbose_name="Object ID")),
                (
                    "changes",
                    models.JSONField(blank=True, default=dict, verbose_name="Changes"),
                ),
                (
                    "extra_info",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="Extra info"
                    ),
                ),
                (
                    "request_info",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="Request info"
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                        verbose_name="Content type",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Log",
                "verbose_name_plural": "Logs",
                "ordering": ["-created_on"],
            },
        ),
        migrations.AddIndex(
            model_name="log",
            index=models.Index(
                fields=["content_type", "object_id"],
                name="logs_log_content_object_idx",
            ),
        ),
    ]
