from django.db import migrations, models
from django.contrib.postgres.operations import AddIndexConcurrently


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("contacts", "0009_alter_contact_imported_history_url"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="contact",
            index=models.Index(
                fields=["name"],
                name="contact_name_idx",
                condition=models.Q(name__isnull=False),
            ),
        ),
    ]
