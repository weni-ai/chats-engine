# Generated by Django 4.1.2 on 2025-04-24 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0010_message_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="message",
            name="metadata",
            field=models.JSONField(
                blank=True, default=dict, null=True, verbose_name="message metadata"
            ),
        ),
    ]
