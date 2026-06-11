from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Moves the automatic message classification to `AutomaticMessage`.

    - Relaxes the `room` relation from OneToOne to ForeignKey so the same
      room can receive multiple automatic messages (welcome, inactivity
      warning, inactivity closure).
    - Adds `automatic_message_type` with default `automatic_open`, which
      correctly classifies every legacy row (the only kind that existed
      before the inactivity feature).

    No backfill on `msgs_message` is required: the default applied by
    Postgres covers every existing `AutomaticMessage` row, and the
    `msgs_message` table is left untouched.
    """

    dependencies = [
        ("msgs", "0017_alter_messagemedia_media_file"),
        ("rooms", "0030_roomnotemedia"),
    ]

    operations = [
        migrations.AlterField(
            model_name="automaticmessage",
            name="room",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="automatic_messages",
                to="rooms.room",
            ),
        ),
        migrations.AddField(
            model_name="automaticmessage",
            name="automatic_message_type",
            field=models.CharField(
                choices=[
                    ("automatic_open", "Automatic open"),
                    ("inactive_warning", "Inactive warning"),
                    ("inactive_close", "Inactive close"),
                ],
                default="automatic_open",
                help_text=(
                    "Classification for automatic messages sent by the system "
                    "(welcome, inactivity warning, inactivity closure)."
                ),
                max_length=32,
                verbose_name="automatic message type",
            ),
        ),
    ]
