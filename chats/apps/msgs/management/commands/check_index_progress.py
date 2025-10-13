from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Check and fix migration state after pod termination during index creation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--migration-name",
            type=str,
            default="0016_messagemedia_message_media_content_type_idx",
            help="Name of the migration to check",
        )
        parser.add_argument(
            "--index-name",
            type=str,
            default="message_media_content_type_idx",
            help="Name of the index to check",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Automatically fix migration state if index exists",
        )

    def handle(self, *args, **options):
        migration_name = options["migration_name"]
        index_name = options["index_name"]
        fix_mode = options["fix"]

        with connection.cursor() as cursor:
            # Check if index exists
            cursor.execute(
                """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE indexname = %s
                """,
                [index_name],
            )

            index_info = cursor.fetchone()

            if index_info:
                self.stdout.write(self.style.SUCCESS(f"✅ Index {index_name} exists!"))
                self.stdout.write(f"Schema: {index_info[0]}")
                self.stdout.write(f"Table: {index_info[1]}")
                self.stdout.write(f"Definition: {index_info[3]}")

                # Check if index is still being built
                try:
                    cursor.execute(
                        """
                        SELECT 
                            pid,
                            phase,
                            blocks_total,
                            blocks_done,
                            CASE 
                                WHEN blocks_total > 0 
                                THEN ROUND((blocks_done::float / blocks_total) * 100, 2)
                                ELSE 0 
                            END AS progress_percent
                        FROM pg_stat_progress_create_index
                        WHERE relid::regclass::text ILIKE %s
                        """,
                        [f"%{index_name}%"],
                    )

                    progress_info = cursor.fetchall()

                    if progress_info:
                        self.stdout.write(
                            self.style.WARNING("⚠️  Index is still being built!")
                        )
                        for row in progress_info:
                            self.stdout.write(f"PID: {row[0]}")
                            self.stdout.write(f"Phase: {row[1]}")
                            self.stdout.write(f"Progress: {row[4]}%")
                            self.stdout.write(f"Blocks: {row[3]}/{row[2]}")

                        if fix_mode:
                            self.stdout.write(
                                self.style.ERROR(
                                    "❌ Cannot fix migration state while index is still being built!"
                                )
                            )
                            return
                    else:
                        self.stdout.write(
                            self.style.SUCCESS("✅ Index creation completed!")
                        )

                except Exception as e:
                    self.stdout.write(f"Note: {e}")

                # Check migration state
                cursor.execute(
                    """
                    SELECT * FROM django_migrations 
                    WHERE app = 'msgs' AND name = %s
                    """,
                    [migration_name],
                )

                migration_info = cursor.fetchone()

                if migration_info:
                    self.stdout.write(
                        f"Migration status: Applied on {migration_info[2]}"
                    )
                    if fix_mode:
                        self.stdout.write(
                            self.style.SUCCESS("✅ Migration state is correct")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️  Migration not found in django_migrations table"
                        )
                    )
                    if fix_mode:
                        # Mark migration as applied
                        cursor.execute(
                            """
                            INSERT INTO django_migrations (app, name, applied)
                            VALUES (%s, %s, NOW())
                            """,
                            ["msgs", migration_name],
                        )
                        self.stdout.write(
                            self.style.SUCCESS("✅ Migration marked as applied")
                        )

            else:
                self.stdout.write(self.style.ERROR(f"❌ Index {index_name} not found"))

                # Check if there's a partial index (invalid state)
                cursor.execute(
                    """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE tablename = 'msgs_messagemedia' 
                      AND indexname ILIKE %s
                    """,
                    [f"%{index_name}%"],
                )

                partial_indexes = cursor.fetchall()
                if partial_indexes:
                    self.stdout.write(
                        self.style.WARNING("⚠️  Found partial/invalid indexes:")
                    )
                    for idx in partial_indexes:
                        self.stdout.write(f"  - {idx[2]}: {idx[3]}")

                    if fix_mode:
                        self.stdout.write(
                            self.style.ERROR(
                                "❌ Manual cleanup required for partial indexes"
                            )
                        )
                else:
                    self.stdout.write("No partial indexes found")

                    if fix_mode:
                        self.stdout.write(
                            self.style.SUCCESS("✅ Safe to re-run migration")
                        )

        if not fix_mode:
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write("To automatically fix migration state, run:")
            self.stdout.write(
                f"python manage.py check_index_progress --fix --migration-name {migration_name} --index-name {index_name}"
            )
