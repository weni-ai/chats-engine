from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("msgs", "0028_bulkquickmessagesend_bulkquickmessagesendmessage"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="messagemedia",
                    name="message",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="medias",
                        to="msgs.message",
                        verbose_name="Message",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE msgs_messagemedia ALTER COLUMN message_id DROP NOT NULL;",
                    reverse_sql="ALTER TABLE msgs_messagemedia ALTER COLUMN message_id SET NOT NULL;",
                ),
            ],
        ),
    ]
