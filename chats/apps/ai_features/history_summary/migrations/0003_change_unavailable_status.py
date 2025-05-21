from django.db import migrations


def change_unavailable_status(apps, schema_editor):
    HistorySummary = apps.get_model("history_summary", "HistorySummary")
    HistorySummary.objects.filter(status="UNAVAILABLE ").update(status="UNAVAILABLE")


class Migration(migrations.Migration):
    dependencies = [
        ("history_summary", "0002_alter_historysummary_status"),
    ]

    operations = [
        migrations.RunPython(
            code=change_unavailable_status,
        ),
    ]
