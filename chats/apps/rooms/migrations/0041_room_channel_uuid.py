from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0040_room_last_message_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="channel_uuid",
            field=models.UUIDField(
                blank=True,
                help_text=(
                    "Weni Web Chat channel UUID used in the room, snapshotted "
                    "from the copilot integration on close."
                ),
                null=True,
                verbose_name="WWC channel UUID",
            ),
        ),
    ]
