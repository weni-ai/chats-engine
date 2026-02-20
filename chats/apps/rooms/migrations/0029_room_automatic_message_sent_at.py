from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0028_alter_roomnote_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="automatic_message_sent_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Automatic message sent at"
            ),
        ),
    ]
