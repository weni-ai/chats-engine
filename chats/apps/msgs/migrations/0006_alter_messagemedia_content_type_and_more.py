# Generated by Django 4.1.2 on 2023-03-23 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0005_alter_messagemedia_media_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="messagemedia",
            name="content_type",
            field=models.CharField(max_length=300, verbose_name="Content Type"),
        ),
        migrations.AlterField(
            model_name="messagemedia",
            name="media_file",
            field=models.FileField(
                blank=True,
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Media File",
            ),
        ),
    ]
