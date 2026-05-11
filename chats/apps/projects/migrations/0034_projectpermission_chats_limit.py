from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0033_projectpermission_is_deleted"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectpermission",
            name="custom_rooms_limit",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Custom rooms limit",
            ),
        ),
        migrations.AddField(
            model_name="projectpermission",
            name="is_custom_limit_active",
            field=models.BooleanField(
                default=False,
                verbose_name="Is custom limit active?",
            ),
        ),
    ]
