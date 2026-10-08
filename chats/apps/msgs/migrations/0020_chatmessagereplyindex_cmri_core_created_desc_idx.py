from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds a composite ``(external_id_core, -created_on)`` index on
    ``ChatMessageReplyIndex`` to serve the WAMID-core fallback query
    (``WHERE external_id_core = ? ORDER BY created_on DESC LIMIT 1``).

    Purely additive: the standalone ``external_id_core`` index added in
    0019 is preserved. Adding a B-tree index on a column that is mostly
    NULL right after rollout is cheap; running the migration in a single
    statement is fine in this scale.
    """

    dependencies = [
        ("msgs", "0019_chatmessagereplyindex_external_id_core"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="chatmessagereplyindex",
            index=models.Index(
                fields=["external_id_core", "-created_on"],
                name="cmri_core_created_desc_idx",
            ),
        ),
    ]
