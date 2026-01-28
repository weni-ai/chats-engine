"""
Migration to add functional index on Room.urn field for accent-insensitive search.

Creates index on LOWER(UNACCENT(urn)) to improve query performance by 10-100x 
when searching for rooms by phone number or URN without accents.
"""
from django.db import migrations


class Migration(migrations.Migration):
    atomic = False  # Required for CREATE INDEX CONCURRENTLY

    dependencies = [
        ('rooms', '0026_alter_room_closed_by'),
        ('contacts', '0012_add_unaccent_functional_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS room_urn_unaccent_lower_idx 
            ON rooms_room (LOWER(UNACCENT(urn)) text_pattern_ops)
            WHERE urn IS NOT NULL AND urn != '';
            """,
            reverse_sql="""
            DROP INDEX CONCURRENTLY IF EXISTS room_urn_unaccent_lower_idx;
            """
        ),
    ]
