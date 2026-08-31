from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("queues", "0012_queue_bond_flows_queue"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="selected_flows",
            field=models.JSONField(
                blank=True, default=list, verbose_name="Selected flows"
            ),
        ),
    ]
