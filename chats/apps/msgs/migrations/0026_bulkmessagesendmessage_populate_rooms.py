from django.db import migrations, models
import django.db.models.deletion
from django.db.models import OuterRef, Subquery


def populate_bulk_message_send_message_rooms(apps, schema_editor):
    BulkMessageSendMessage = apps.get_model("msgs", "BulkMessageSendMessage")
    Message = apps.get_model("msgs", "Message")

    room_subquery = Subquery(
        Message.objects.filter(pk=OuterRef("message_id")).values("room")[:1]
    )

    BulkMessageSendMessage.objects.filter(
        room__isnull=True, message__isnull=False
    ).update(room=room_subquery)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0039_rooms_violation_indexes"),
        ("msgs", "0025_bulkmessagesendmessage_errors_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_bulk_message_send_message_rooms,
            reverse_noop,
        ),
        migrations.AlterField(
            model_name="bulkmessagesendmessage",
            name="room",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bulk_message_send_messages",
                to="rooms.room",
                verbose_name="room",
            ),
        ),
    ]
