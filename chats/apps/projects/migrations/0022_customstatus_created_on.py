# Generated by Django 4.1.2 on 2025-02-11 19:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0021_customstatustype_customstatus"),
    ]

    operations = [
        migrations.AddField(
            model_name="customstatus",
            name="created_on",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                editable=False,
                verbose_name="Created on",
            ),
        ),
    ]
