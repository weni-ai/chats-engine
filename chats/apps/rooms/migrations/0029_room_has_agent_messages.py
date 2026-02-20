from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0028_alter_roomnote_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="has_agent_messages",
            field=models.BooleanField(
                default=False, verbose_name="Has agent messages"
            ),
        ),
    ]
