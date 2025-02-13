# Generated by Django 4.1.2 on 2025-02-12 18:03

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0023_remove_customstatus_id_customstatus_modified_on_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customstatustype",
            name="id",
        ),
        migrations.AddField(
            model_name="customstatustype",
            name="created_on",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="Created on",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="customstatustype",
            name="modified_on",
            field=models.DateTimeField(auto_now=True, verbose_name="Modified on"),
        ),
        migrations.AddField(
            model_name="customstatustype",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4, primary_key=True, serialize=False
            ),
        ),
    ]
