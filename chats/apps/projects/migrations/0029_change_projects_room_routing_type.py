from django.db import migrations


def change_room_routing_type(apps, schema_editor):
    Project = apps.get_model("projects", "Project")

    Project.objects.filter(room_routing_type="GENERAL").update(
        room_routing_type="QUEUE_PRIORITY"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0028_alter_project_room_routing_type"),
    ]

    operations = [
        migrations.RunPython(change_room_routing_type),
    ]
