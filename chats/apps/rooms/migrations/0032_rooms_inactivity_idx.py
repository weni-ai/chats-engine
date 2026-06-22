from django.db import migrations


class Migration(migrations.Migration):
    """
    No-op alias for staging compatibility.
    In main this migration adds the inactivity index, but in staging that
    was already done by 0031_rooms_inactivity_idx. This file exists so that
    0033_room_automatic_closed (identical to main) can resolve its dependency.
    """

    dependencies = [
        ("rooms", "0031_rooms_inactivity_idx"),
    ]

    operations = []
