from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0011_unique_contact_external_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="document",
            field=models.CharField(
                blank=True, max_length=50, null=True, verbose_name=_("document")
            ),
        ),
    ]
