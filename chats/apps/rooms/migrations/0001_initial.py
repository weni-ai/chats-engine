# Generated by Django 4.0.4 on 2022-06-10 19:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contacts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=120, verbose_name="Name")),
            ],
            options={
                "verbose_name": "Room Tag",
                "verbose_name_plural": "Room Tags",
            },
        ),
        migrations.CreateModel(
            name="Room",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started_at", models.DateTimeField(verbose_name="Started at")),
                (
                    "ended_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Ended at"
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contacts.contact",
                        verbose_name="messages",
                    ),
                ),
                (
                    "tags",
                    models.ManyToManyField(
                        blank=True, null=True, to="rooms.roomtag", verbose_name="tags"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="messages",
                    ),
                ),
            ],
            options={
                "verbose_name": "Room",
                "verbose_name_plural": "Rooms",
            },
        ),
    ]
