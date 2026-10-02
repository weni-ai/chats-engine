from django.db import migrations, models


def forwards(apps, schema_editor):
    ProjectPermission = apps.get_model("projects", "ProjectPermission")
    # Previous desk values: 1 admin, 2 attendant.
    # Connect values: 3 moderator, 5 chat user.
    ProjectPermission.objects.filter(role=1).update(role=3)
    ProjectPermission.objects.filter(role=2).update(role=5)


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0037_project_is_live_desk_copilot"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="projectpermission",
            name="role",
            field=models.PositiveIntegerField(
                choices=[
                    (0, "not set"),
                    (1, "viewer"),
                    (2, "contributor"),
                    (3, "moderator"),
                    (4, "support"),
                    (5, "chat user"),
                    (6, "marketing"),
                ],
                default=0,
                verbose_name="role",
            ),
        ),
    ]
