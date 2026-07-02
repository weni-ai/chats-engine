from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds ``external_id_core`` to ``ChatMessageReplyIndex``.

    The new column stores the stable hex "core" of a WAMID so replies can be
    resolved even when Meta sends a different envelope inside ``context.id``
    (``wamid.HBgM...`` vs ``wamid.HBgT...``). The column is nullable so the
    migration is cheap on large tables — legacy rows simply stay ``NULL`` and
    only new ``create_reply_index`` writes populate it.
    """

    dependencies = [
        ("msgs", "0019_automaticmessage_type_and_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessagereplyindex",
            name="external_id_core",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                verbose_name="External ID core",
            ),
        ),
    ]
