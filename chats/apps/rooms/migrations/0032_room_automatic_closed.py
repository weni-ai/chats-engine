from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rooms", "0031_rooms_inactivity_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="automatic_closed",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True when the room was closed automatically by the "
                    "system (e.g. inactivity timeout) rather than by a "
                    "human agent."
                ),
                verbose_name="automatic closed?",
            ),
        ),
    ]
