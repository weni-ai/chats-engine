from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("contacts", "0012_contact_document"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="contact",
            index=models.Index(
                condition=models.Q(("document__isnull", False)),
                fields=["document"],
                name="contact_document_idx",
            ),
        ),
        AddIndexConcurrently(
            model_name="contact",
            index=models.Index(
                condition=models.Q(("email__isnull", False)),
                fields=["email"],
                name="contact_email_idx",
            ),
        ),
    ]
