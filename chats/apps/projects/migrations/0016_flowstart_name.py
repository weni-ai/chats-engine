# Generated by Django 4.1.2 on 2023-05-02 19:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0015_flowstart_is_deleted_flowstart_room_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="flowstart",
            name="name",
            field=models.TextField(
                blank=True, default="", null=True, verbose_name="flow name"
            ),
        ),
    ]
