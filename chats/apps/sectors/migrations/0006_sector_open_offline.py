# Generated by Django 4.1.2 on 2023-06-27 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sectors", "0005_remove_sector_rooms_limit_greater_than_zero"),
    ]

    operations = [
        migrations.AddField(
            model_name="sector",
            name="open_offline",
            field=models.BooleanField(
                default=True, verbose_name="Open room when all agents are offline?"
            ),
        ),
    ]
