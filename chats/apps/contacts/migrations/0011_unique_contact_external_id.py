from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0010_enable_unaccent_extension'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='contact',
            constraint=models.UniqueConstraint(
                condition=models.Q(('external_id__isnull', False)),
                fields=('external_id',),
                name='unique_contact_external_id',
            ),
        ),
    ]
