# Generated by Django 4.1.2 on 2025-03-10 19:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0023_customstatus_project_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customstatus",
            name="project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="projects.project",
            ),
        ),
        migrations.AddConstraint(
            model_name="customstatustype",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("name", "project"),
                name="unique_custom_status",
            ),
        ),
    ]
