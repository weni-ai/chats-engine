# Generated by Django 4.1.2 on 2023-10-06 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0009_alter_room_callback_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="room",
            name="urn",
            field=models.TextField(
                blank=True, default="", null=True, verbose_name="urn"
            ),
        ),
    ]
