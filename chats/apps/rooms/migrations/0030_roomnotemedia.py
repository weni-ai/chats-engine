import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import chats.apps.rooms.models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0029_room_automatic_message_sent_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomNoteMedia",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="Created on",
                    ),
                ),
                (
                    "modified_on",
                    models.DateTimeField(auto_now=True, verbose_name="Modified on"),
                ),
                (
                    "content_type",
                    models.CharField(max_length=300, verbose_name="Content Type"),
                ),
                (
                    "media_file",
                    models.FileField(
                        blank=True,
                        max_length=300,
                        null=True,
                        upload_to=chats.apps.rooms.models.room_note_media_upload_to,
                        verbose_name="Media File",
                    ),
                ),
                (
                    "media_url",
                    models.TextField(blank=True, null=True, verbose_name="Media url"),
                ),
                (
                    "note",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="medias",
                        to="rooms.roomnote",
                        verbose_name="room note",
                    ),
                ),
            ],
            options={
                "verbose_name": "RoomNoteMedia",
                "verbose_name_plural": "RoomNoteMedias",
            },
        ),
        migrations.AddIndex(
            model_name="roomnotemedia",
            index=models.Index(
                fields=["content_type"], name="room_note_media_ct_idx"
            ),
        ),
    ]
