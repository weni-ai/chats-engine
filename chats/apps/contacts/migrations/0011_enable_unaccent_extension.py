from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0010_add_index_to_contact_name'),
    ]

    operations = [
        UnaccentExtension(),
    ]
