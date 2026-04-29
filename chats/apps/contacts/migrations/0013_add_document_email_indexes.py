from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0012_contact_document"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                condition=models.Q(("document__isnull", False)),
                fields=["document"],
                name="contact_document_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                condition=models.Q(("email__isnull", False)),
                fields=["email"],
                name="contact_email_idx",
            ),
        ),
    ]
