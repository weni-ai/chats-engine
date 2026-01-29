from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0009_alter_contact_imported_history_url'),
    ]

    operations = [
        UnaccentExtension(),
    ]

