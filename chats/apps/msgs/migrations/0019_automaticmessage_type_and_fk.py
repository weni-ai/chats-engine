import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("msgs", "0018_message_automatic_message_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="automaticmessage",
            name="room",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="automatic_messages",
                to="rooms.room",
            ),
        ),
        migrations.AddField(
            model_name="automaticmessage",
            name="automatic_message_type",
            field=models.CharField(
                choices=[
                    ("automatic_open", "Automatic open"),
                    ("inactive_warning", "Inactive warning"),
                    ("inactive_close", "Inactive close"),
                ],
                default="automatic_open",
                help_text=(
                    "Classification for automatic messages sent by the system "
                    "(welcome, inactivity warning, inactivity closure)."
                ),
                max_length=32,
                verbose_name="automatic message type",
            ),
        ),
    ]
