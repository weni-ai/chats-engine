from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0030_room_is_inactive"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="room",
            index=models.Index(
                fields=["is_active", "is_inactive", "is_waiting", "last_interaction"],
                name="rooms_inactivity_idx",
            ),
        ),
    ]
