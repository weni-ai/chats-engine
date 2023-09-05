# Generated by Django 4.1.2 on 2023-08-30 17:18

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0017_project_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateType",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created on"),
                ),
                (
                    "modified_on",
                    models.DateTimeField(auto_now=True, verbose_name="Modified on"),
                ),
                (
                    "is_deleted",
                    models.BooleanField(default=False, verbose_name="is deleted?"),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "setup",
                    models.JSONField(default=dict, verbose_name="Template Setup"),
                ),
            ],
            options={
                "verbose_name": "TemplateType",
                "verbose_name_plural": "TemplateTypes",
            },
        ),
        migrations.AddField(
            model_name="project",
            name="is_template",
            field=models.BooleanField(default=False, verbose_name="is template?"),
        ),
        migrations.AddField(
            model_name="project",
            name="template_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="projects.templatetype",
                verbose_name="template type",
            ),
        ),
    ]
