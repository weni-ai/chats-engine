from chats.apps.dashboard.models import MetricGoal

VALID_METRICS = {choice[0] for choice in MetricGoal.METRIC_CHOICES}

UNIT_TO_SECONDS = {
    MetricGoal.UNIT_SECOND: 1,
    MetricGoal.UNIT_MINUTE: 60,
    MetricGoal.UNIT_HOUR: 3600,
}


def threshold_seconds_to_unit_value(threshold_seconds: int, unit: str) -> int:
    """
    Returns the threshold expressed in the configured unit (s/m/h).

    Storage is canonical in seconds, so a 5-minute threshold is stored as
    300 and projected back to 5 here. Falls back to the raw value when the
    unit is unknown.
    """
    seconds_in_unit = UNIT_TO_SECONDS.get(unit, 1)
    if seconds_in_unit <= 0:
        return threshold_seconds
    return threshold_seconds // seconds_in_unit
