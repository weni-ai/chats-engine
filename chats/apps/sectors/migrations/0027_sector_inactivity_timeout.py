from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sectors", "0026_sector_automatic_message_queue_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sector",
            name="inactivity_timeout",
            field=models.JSONField(
                blank=True,
                default=None,
                help_text=(
                    "Configuration for inactivity warning message and automatic "
                    "room closure. See `chats.apps.sectors.constants."
                    "get_default_inactivity_timeout`."
                ),
                null=True,
                verbose_name="inactivity timeout",
            ),
        ),
    ]
