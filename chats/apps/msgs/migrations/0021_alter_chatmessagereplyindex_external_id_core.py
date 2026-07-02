from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Widens ``ChatMessageReplyIndex.external_id_core`` from
    ``CharField(max_length=64)`` to an unbounded ``TextField``.

    Production incident: the LID-based WAMID envelope (``HBgT<LID>...``,
    emitted by Meta when a contact replies to their own earlier message)
    wraps a longer internal id than the other envelopes. Its hex core is
    consistently 66 characters, which is not a rare outlier — every WAMID
    matching that envelope produces a core of that length. That overflowed
    the 64-char column and raised ``DataError: value too long for type
    character varying(64)`` on every incoming message whose WAMID happened
    to use that envelope, blocking message creation in production.

    Rather than pick a new fixed cap that could overflow again with a
    future Meta envelope, this switches the column to ``text``: Postgres
    indexes ``text`` the same way as ``varchar`` (the existing standalone
    index and the ``cmri_core_created_desc_idx`` composite index from 0020
    are preserved), and the values stored here are always small (well
    under 1KB), so there is no practical cost. ``ALTER COLUMN ... TYPE
    text`` from ``varchar`` is a fast, in-place metadata-only change in
    Postgres (no table rewrite), so this is safe to run without downtime.
    """

    dependencies = [
        ("msgs", "0020_chatmessagereplyindex_cmri_core_created_desc_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatmessagereplyindex",
            name="external_id_core",
            field=models.TextField(
                blank=True, db_index=True, null=True, verbose_name="External ID core"
            ),
        ),
    ]
