import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assisted_sales", "0002_copilotmessagefeedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="copilotintegration",
            name="is_connected",
            field=models.BooleanField(default=True, verbose_name="Is connected"),
        ),
        migrations.AddField(
            model_name="copilotintegration",
            name="disconnected_on",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Disconnected on"
            ),
        ),
        migrations.AddField(
            model_name="copilotintegration",
            name="disconnected_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="disconnected_copilot_integrations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Disconnected by",
            ),
        ),
    ]
