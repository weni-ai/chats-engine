from django.db import migrations, models
from django.contrib.postgres.operations import AddIndexConcurrently


class Migration(migrations.Migration):
    atomic = False
    dependencies = [
        ("msgs", "0015_automaticmessage"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="messagemedia",
            index=models.Index(
                fields=["content_type"], name="message_media_content_type_idx"
            ),
        ),
    ]
