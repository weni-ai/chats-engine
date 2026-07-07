from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("queues", "0008_queueauthorization_is_deleted"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="queue_purpose",
            field=models.TextField(blank=True, null=True, verbose_name="Queue purpose"),
        ),
    ]
