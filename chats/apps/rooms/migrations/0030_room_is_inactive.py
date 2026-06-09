from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0029_room_automatic_message_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="is_inactive",
            field=models.BooleanField(default=False, verbose_name="is inactive?"),
        ),
    ]
