# Generated by Django 4.1.2 on 2025-02-18 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0021_customstatustype_customstatus"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customstatus",
            name="break_time",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Custom status timming"
            ),
        ),
    ]
