from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("rooms", "0041_room_channel_uuid"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="room",
            index=models.Index(
                fields=["urn"],
                name="rooms_room_urn_prefix_idx",
                opclasses=["text_pattern_ops"],
                condition=Q(urn__isnull=False) & ~Q(urn=""),
            ),
        ),
    ]
