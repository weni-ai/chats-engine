from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("queues", "0011_merge_20260708_1718"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="bond_flows_queue",
            field=models.BooleanField(default=False, verbose_name="Bond flows queue"),
        ),
    ]
