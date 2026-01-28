from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('rooms', '0023_room_closed_by_room_first_user_assigned_at_and_more'),
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
