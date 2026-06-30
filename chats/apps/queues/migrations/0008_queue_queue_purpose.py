from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("queues", "0007_queue_created_by_queue_deleted_by_queue_modified_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="queue_purpose",
            field=models.TextField(blank=True, null=True, verbose_name="Queue purpose"),
        ),
    ]
