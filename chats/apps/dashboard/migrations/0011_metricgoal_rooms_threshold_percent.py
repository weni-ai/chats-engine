import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0010_metricgoal"),
    ]

    operations = [
        migrations.AddField(
            model_name="metricgoal",
            name="rooms_threshold_percent",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(100),
                ],
                verbose_name="Rooms threshold percent",
                help_text=(
                    "When set, takes precedence over rooms_threshold_count "
                    "and represents the percentage of active rooms in "
                    "violation required to trigger the alert."
                ),
            ),
        ),
    ]
