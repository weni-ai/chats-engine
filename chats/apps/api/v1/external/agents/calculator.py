from datetime import datetime, timedelta

from django.utils import timezone

ONLINE_STATES = {"ONLINE", "In-Service"}


def _parse_ts(raw):
    return datetime.fromisoformat(raw)


def calculate_online_time(all_status_changes, close_open_with_now=False):
    """
    Given a flat, chronologically ordered list of status change events
    (potentially spanning multiple days), returns the total online time
    as a timedelta.

    Events with status in ONLINE_STATES are considered "online".
    Everything else (OFFLINE, BREAK, etc.) closes the current online interval.

    If close_open_with_now is True and the last event is an online state,
    the interval is closed with timezone.now().
    """
    if not all_status_changes:
        return timedelta()

    total = timedelta()
    online_start = None

    for event in all_status_changes:
        ts = _parse_ts(event["timestamp"])
        is_online = event.get("status") in ONLINE_STATES

        if is_online and online_start is None:
            online_start = ts
        elif not is_online and online_start is not None:
            total += ts - online_start
            online_start = None

    if online_start is not None and close_open_with_now:
        total += timezone.now() - online_start

    return total


def build_agent_log_maps(project_uuid, start_date=None, end_date=None):
    """
    Single query on AgentStatusLog for the given project and date range.
    Returns a tuple (status_log_map, online_time_map):
      - status_log_map: {email: last_change_timestamp}
      - online_time_map: {email: online_minutes (float)}

    Defaults to today if no dates are provided.
    If end_date includes today, open online intervals are closed with now().
    """
    from chats.apps.projects.models.models import AgentStatusLog

    today = timezone.now().date()
    if start_date is None:
        start_date = today
    if end_date is None:
        end_date = today

    logs = (
        AgentStatusLog.objects.filter(
            project__uuid=project_uuid,
            log_date__range=(start_date, end_date),
        )
        .order_by("agent__email", "log_date")
        .values_list("agent__email", "log_date", "status_changes")
    )

    agent_events = {}
    last_day_changes = {}

    for email, log_date, changes in logs:
        if changes and isinstance(changes, list) and len(changes) > 0:
            agent_events.setdefault(email, []).extend(changes)
            if log_date == end_date or (end_date is None and log_date == today):
                last_day_changes[email] = changes

    status_log_map = {}
    for email, changes in last_day_changes.items():
        status_log_map[email] = changes[-1].get("timestamp")

    close_with_now = end_date >= today

    online_time_map = {}
    for email, events in agent_events.items():
        events.sort(key=lambda e: e["timestamp"])
        dt = calculate_online_time(events, close_open_with_now=close_with_now)
        online_time_map[email] = round(dt.total_seconds() / 60, 2)

    return status_log_map, online_time_map
