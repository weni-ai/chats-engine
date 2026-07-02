from django.db import migrations
from django.db.models import Subquery, OuterRef


def populate_roompin_project(apps, schema_editor):
    RoomPin = apps.get_model("rooms", "RoomPin")
    Room = apps.get_model("rooms", "Room")

    project_subquery = Subquery(
        Room.objects.filter(pk=OuterRef("room_id")).values("queue__sector__project")[:1]
    )

    RoomPin.objects.filter(project__isnull=True).update(project=project_subquery)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0036_roompin_project"),
    ]

    operations = [
        migrations.RunPython(populate_roompin_project, reverse_noop),
    ]
