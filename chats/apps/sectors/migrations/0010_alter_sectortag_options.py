# Generated by Django 4.1.2 on 2023-10-16 11:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sectors", "0009_sector_config"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="sectortag",
            options={
                "ordering": ["name"],
                "verbose_name": "Sector Tag",
                "verbose_name_plural": "Sector Tags",
            },
        ),
    ]
