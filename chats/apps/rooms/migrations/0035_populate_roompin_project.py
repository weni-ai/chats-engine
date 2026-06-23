from django.db import migrations
from django.db.models import F


def populate_roompin_project(apps, schema_editor):
    RoomPin = apps.get_model("rooms", "RoomPin")
    RoomPin.objects.filter(project__isnull=True).update(
        project=F("room__queue__sector__project")
    )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0034_roompin_project"),
    ]

    operations = [
        migrations.RunPython(populate_roompin_project, reverse_noop),
    ]
