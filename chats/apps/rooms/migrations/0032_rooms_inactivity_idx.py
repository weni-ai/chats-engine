from django.db import migrations, models
from django.contrib.postgres.operations import AddIndexConcurrently


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("rooms", "0031_room_is_inactive"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="room",
            index=models.Index(
                fields=["is_active", "is_inactive", "is_waiting", "last_interaction"],
                name="rooms_inactivity_idx",
            ),
        ),
    ]
