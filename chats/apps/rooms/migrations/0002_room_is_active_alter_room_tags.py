# Generated by Django 4.0.4 on 2022-06-10 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="is active?"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="room",
            name="tags",
            field=models.ManyToManyField(to="rooms.roomtag", verbose_name="tags"),
        ),
    ]
