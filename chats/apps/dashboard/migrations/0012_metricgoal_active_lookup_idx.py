from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("dashboard", "0011_metricgoal_rooms_threshold_percent"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="metricgoal",
            index=models.Index(
                fields=["metric", "project"],
                name="metric_goal_active_lookup_idx",
                condition=Q(is_active=True),
            ),
        ),
    ]
