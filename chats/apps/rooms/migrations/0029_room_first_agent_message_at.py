from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0028_alter_roomnote_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="first_agent_message_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="First agent message at"
            ),
        ),
    ]
