# Generated by Django 4.1.2 on 2023-05-22 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("queues", "0003_queue_default_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="is_deleted",
            field=models.BooleanField(default=False, verbose_name="is deleted?"),
        ),
    ]