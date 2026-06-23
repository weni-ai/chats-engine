from chats.apps.dashboard.models import MetricGoal

VALID_METRICS = {choice[0] for choice in MetricGoal.METRIC_CHOICES}

UNIT_TO_SECONDS = {
    MetricGoal.UNIT_SECOND: 1,
    MetricGoal.UNIT_MINUTE: 60,
    MetricGoal.UNIT_HOUR: 3600,
}
