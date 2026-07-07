from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("queues", "0009_remove_queueauthorization_unique_queue_auth_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="queue_purpose",
            field=models.TextField(blank=True, null=True, verbose_name="Queue purpose"),
        ),
    ]
