from django.db import migrations, models


def backfill_automatic_open_type(apps, schema_editor):
    """
    Mark every legacy welcome message (`AutomaticMessage` OneToOne) with the
    new explicit `automatic_message_type='automatic_open'` so the
    `is_automatic_message` property keeps returning True for them after we
    switched the source of truth from the OneToOne reverse relation to the
    new field.
    """
    Message = apps.get_model("msgs", "Message")
    AutomaticMessage = apps.get_model("msgs", "AutomaticMessage")

    message_ids = AutomaticMessage.objects.values_list("message_id", flat=True)
    Message.objects.filter(pk__in=list(message_ids)).update(
        automatic_message_type="automatic_open"
    )


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("msgs", "0017_alter_messagemedia_media_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="automatic_message_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("automatic_open", "Automatic open"),
                    ("inactive_warning", "Inactive warning"),
                    ("inactive_close", "Inactive close"),
                ],
                help_text=(
                    "Classification for automatic messages sent by the system "
                    "(welcome, inactivity warning, inactivity closure)."
                ),
                max_length=32,
                null=True,
                verbose_name="automatic message type",
            ),
        ),
        migrations.RunPython(backfill_automatic_open_type, noop_reverse),
    ]
