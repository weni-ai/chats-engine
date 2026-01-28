"""
Migration to add functional indexes for accent-insensitive search.

Creates indexes on LOWER(UNACCENT(field)) expressions to improve query 
performance by 10-100x when searching for contacts without accents.

Example: Searching "angela" will find "Ângela", "ANGELA", etc.
"""
from django.db import migrations


class Migration(migrations.Migration):
    atomic = False  # Required for CREATE INDEX CONCURRENTLY

    dependencies = [
        ('contacts', '0010_enable_unaccent_extension'),
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
