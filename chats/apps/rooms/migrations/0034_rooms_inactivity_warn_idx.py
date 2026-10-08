from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("rooms", "0033_room_automatic_closed"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="room",
            index=models.Index(
                fields=["last_interaction"],
                name="rooms_inactivity_warn_idx",
                condition=models.Q(
                    is_active=True,
                    is_inactive=False,
                    is_waiting=False,
                    user__isnull=False,
                    last_message_user__isnull=False,
                ),
            ),
        ),
    ]
