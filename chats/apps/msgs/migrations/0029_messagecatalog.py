from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0028_messagemedia_room_alter_messagemedia_message"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageCatalog",
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
                    "data",
                    models.JSONField(default=dict, verbose_name="catalog data"),
                ),
                (
                    "message",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="catalog",
                        to="msgs.message",
                        verbose_name="Message",
                    ),
                ),
            ],
            options={
                "verbose_name": "Message catalog",
                "verbose_name_plural": "Message catalogs",
            },
        ),
    ]
