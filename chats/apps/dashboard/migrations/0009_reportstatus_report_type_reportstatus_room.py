from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0008_reportstatus_retry_count_and_status"),
        ("rooms", "0029_room_automatic_message_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportstatus",
            name="report_type",
            field=models.CharField(
                choices=[
                    ("custom_dashboard", "Custom Dashboard"),
                    ("room_export", "Room Export"),
                ],
                db_index=True,
                default="custom_dashboard",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="reportstatus",
            name="room",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="export_reports",
                to="rooms.room",
            ),
        ),
    ]
