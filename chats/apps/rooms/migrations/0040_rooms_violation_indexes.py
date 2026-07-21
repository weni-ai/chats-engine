from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("rooms", "0039_alter_roomnote_options_alter_roompin_options_and_more"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="room",
            index=models.Index(
                fields=["project_uuid", "added_to_queue_at"],
                name="rooms_waiting_violation_idx",
                condition=Q(
                    is_active=True,
                    user__isnull=True,
                    added_to_queue_at__isnull=False,
                ),
            ),
        ),
        AddIndexConcurrently(
            model_name="room",
            index=models.Index(
                fields=["project_uuid", "first_user_assigned_at"],
                name="rooms_frt_violation_idx",
                condition=Q(
                    is_active=True,
                    user__isnull=False,
                    first_user_assigned_at__isnull=False,
                ),
            ),
        ),
    ]
