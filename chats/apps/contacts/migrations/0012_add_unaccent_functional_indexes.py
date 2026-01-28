from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('contacts', '0011_enable_unaccent_extension'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS contact_name_unaccent_lower_idx 
            ON contacts_contact (LOWER(UNACCENT(name)) text_pattern_ops)
            WHERE name IS NOT NULL;
            """,
            reverse_sql="""
            DROP INDEX CONCURRENTLY IF EXISTS contact_name_unaccent_lower_idx;
            """
        ),
    ]
