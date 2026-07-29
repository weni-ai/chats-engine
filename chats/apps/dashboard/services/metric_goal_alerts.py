"""Detect Metric Goal violations and drive the Redis state machine.

The service is invoked by a Celery beat sweep every 30 seconds. For each
metric type, we iterate over the configured (and active) ``MetricGoal``
rows and run a small aggregate query against ``rooms_room``. Results are
compared against the previous state stored in Redis so we can identify
transitions and dispatch WebSocket broadcasts and emails accordingly.

Rooms are scoped to a project via ``queue__sector__project`` (a join),
not via the denormalized ``Room.project_uuid`` field, since that field
is only populated by one of the room-creation paths and would otherwise
undercount violations.

Two independent Redis state machines run in parallel:

1. **Widget / project broadcast** (``metric_goal.violated`` /
   ``update`` / ``resolved``): claimed as soon as a single room breaches
   ``threshold_seconds``. Cleared when no rooms remain in breach.
2. **Toast / email** (``metric_goal.alert`` + email): claimed when
   ``email_enabled`` is true and ``violating_count`` crosses into
   ``>= rooms_threshold_count``. Dropping below that count clears the
   toast state so the next climb back to the threshold fires again.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import ceil
from typing import Dict, Iterable, List, Set

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Exists, Max, OuterRef
from django.utils import timezone
from django_redis import get_redis_connection
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.dashboard.models import MetricGoal, RoomMetrics
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)

FEATURE_FLAG_CACHE_KEY_TEMPLATE = "metric_goal_alerts_ff:{project_uuid}"
DEFAULT_FEATURE_FLAG_CACHE_TTL_SECONDS = 30


def is_metric_goal_alerts_enabled(project_uuid: str) -> bool:
    """Whether the metric goal / risk alerts feature is enabled for a project.

    Fails closed (returns ``False``) if the flag can't be evaluated, so a
    GrowthBook outage never turns on alerts for projects that shouldn't
    have them.

    Results are cached briefly so the Celery sweep (and other hot paths)
    do not re-hit GrowthBook on every metric/project check within the
    same short window.
    """
    if not project_uuid:
        return False

    project_uuid = str(project_uuid)
    cache_key = FEATURE_FLAG_CACHE_KEY_TEMPLATE.format(project_uuid=project_uuid)
    cached = cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    try:
        enabled = is_feature_active_for_attributes(
            settings.METRIC_GOAL_ALERTS_FEATURE_FLAG_KEY,
            {"projectUUID": project_uuid},
        )
    except Exception:
        logger.warning(
            "metric_goal: failed to evaluate feature flag for project %s",
            project_uuid,
            exc_info=True,
        )
        return False

    ttl = getattr(
        settings,
        "METRIC_GOAL_ALERTS_FEATURE_FLAG_CACHE_TTL",
        DEFAULT_FEATURE_FLAG_CACHE_TTL_SECONDS,
    )
    if ttl > 0:
        cache.set(cache_key, enabled, ttl)
    return bool(enabled)


STATE_VIOLATING = "violating"
STATE_ALERTING = "alerting"

DEFAULT_STATE_TTL_SECONDS = 30 * 60

STATE_KEY_TEMPLATE = "metric_goal_state:{project_uuid}:{metric}"
ALERT_STATE_KEY_TEMPLATE = "metric_goal_alert_state:{project_uuid}:{metric}"


TRANSITION_NEW = "new"
TRANSITION_UPDATE = "update"
TRANSITION_RESOLVED = "resolved"


@dataclass(frozen=True)
class Violation:
    """A project with one or more rooms currently above ``threshold_seconds``.

    Widget broadcasts (``metric_goal.violated`` / ``update`` / ``resolved``)
    fire as soon as ``violating_count >= 1``. Email/toast
    (``metric_goal.alert``) only fire when ``email_enabled`` is true and
    ``meets_rooms_threshold`` is true (see ``process_violations``).
    """

    project_uuid: str
    metric: str
    violating_count: int
    max_value_seconds: int
    threshold_seconds: int
    rooms_threshold_count: int
    rooms_threshold_percent: int | None = None
    active_rooms_count: int | None = None
    email_enabled: bool = False
    detected_at: datetime = field(default_factory=timezone.now)

    @property
    def meets_rooms_threshold(self) -> bool:
        """Whether enough rooms are in breach to fire email/toast."""
        return self.violating_count >= self.rooms_threshold_count

    # Backwards-compatible alias used by older call sites / docs.
    @property
    def meets_email_threshold(self) -> bool:
        return self.meets_rooms_threshold

    def as_broadcast_payload(self, state: str) -> dict:
        return {
            "project_uuid": self.project_uuid,
            "metric": self.metric,
            "violating_count": self.violating_count,
            "threshold_seconds": self.threshold_seconds,
            "max_value_seconds": self.max_value_seconds,
            "rooms_threshold_count": self.rooms_threshold_count,
            "rooms_threshold_percent": self.rooms_threshold_percent,
            "active_rooms_count": self.active_rooms_count,
            "state": state,
            "detected_at": self.detected_at.isoformat(),
        }


def _build_violation_queryset(metric: str, project_uuid: str, cutoff: datetime):
    """Return the queryset of rooms currently violating the metric.

    Rooms are scoped to the project via ``queue__sector__project`` (the
    same join used by ``MetricGoalBreachService``) instead of the
    denormalized ``Room.project_uuid`` field. That field is only
    populated by one of the room-creation paths (the Flows external
    integration), so filtering by it silently excludes rooms created
    through any other path (API v2, transfers, discussions, etc.),
    undercounting violations and causing thresholds to behave
    inconsistently with what the dashboard shows.
    """
    base = Room.objects.filter(
        queue__sector__project__uuid=project_uuid, is_active=True
    )

    if metric == MetricGoal.METRIC_WAITING_TIME:
        return base.filter(
            user__isnull=True,
            added_to_queue_at__isnull=False,
            added_to_queue_at__lte=cutoff,
        )

    if metric == MetricGoal.METRIC_FIRST_RESPONSE_TIME:
        responded = RoomMetrics.objects.filter(
            room=OuterRef("pk"),
            first_response_time__gt=0,
        )
        return (
            base.filter(
                user__isnull=False,
                first_user_assigned_at__isnull=False,
                first_user_assigned_at__lte=cutoff,
            )
            .annotate(has_responded=Exists(responded))
            .filter(has_responded=False)
        )

    if metric == MetricGoal.METRIC_CONVERSATION_DURATION:
        # Must match MetricGoalBreachService / TimeMetricsService: only
        # rooms currently assigned to an agent count as "in conversation".
        return base.filter(
            user__isnull=False,
            first_user_assigned_at__isnull=False,
            first_user_assigned_at__lte=cutoff,
        )

    raise ValueError(f"Unknown metric: {metric}")


def _max_age_field(metric: str) -> str:
    if metric == MetricGoal.METRIC_WAITING_TIME:
        return "added_to_queue_at"
    return "first_user_assigned_at"


def _resolve_threshold_count(goal_data: dict, active_rooms_count: int | None) -> int:
    percent = goal_data.get("rooms_threshold_percent")
    if percent and active_rooms_count is not None:
        return max(1, ceil(active_rooms_count * percent / 100))
    return goal_data.get("rooms_threshold_count") or (
        MetricGoal.DEFAULT_ROOMS_THRESHOLD_COUNT
    )


def _project_active_room_counts(project_uuids: Iterable[str]) -> Dict[str, int]:
    if not project_uuids:
        return {}
    rows = (
        Room.objects.filter(
            queue__sector__project__uuid__in=list(project_uuids), is_active=True
        )
        .values("queue__sector__project__uuid")
        .annotate(count=Count("uuid"))
    )
    return {str(row["queue__sector__project__uuid"]): row["count"] for row in rows}


def detect_violations(
    metric: str, now: datetime | None = None
) -> List[Violation]:
    """Return the list of projects currently violating ``metric``.

    One small aggregate query is issued per configured ``MetricGoal``.
    With ~230 active projects this stays well within the planner's
    sweet spot and keeps query shapes index-friendly.

    A project is included as soon as at least one room breaches
    ``threshold_seconds``. ``process_violations`` then drives the widget
    state machine on that list and applies the rooms / email gates only
    for toast and email notifications.
    """
    now = now or timezone.now()
    goals = [
        goal
        for goal in MetricGoal.objects.filter(metric=metric, is_active=True).values(
            "project__uuid",
            "threshold_seconds",
            "rooms_threshold_count",
            "rooms_threshold_percent",
            "email_enabled",
        )
        if is_metric_goal_alerts_enabled(str(goal["project__uuid"]))
    ]
    if not goals:
        return []

    project_uuids = [str(g["project__uuid"]) for g in goals]
    needs_active_count = any(g["rooms_threshold_percent"] for g in goals)
    active_counts = (
        _project_active_room_counts(project_uuids) if needs_active_count else {}
    )

    age_field = _max_age_field(metric)
    violations: List[Violation] = []

    for goal in goals:
        project_uuid = str(goal["project__uuid"])
        threshold_seconds = goal["threshold_seconds"]
        cutoff = now - timedelta(seconds=threshold_seconds)

        qs = _build_violation_queryset(metric, project_uuid, cutoff)
        agg = qs.aggregate(count=Count("uuid"), oldest=Max(age_field))
        violating_count = agg["count"] or 0

        if violating_count == 0:
            continue

        active_count = active_counts.get(project_uuid)
        threshold_count = _resolve_threshold_count(goal, active_count)

        oldest = agg["oldest"]
        max_age = int((now - oldest).total_seconds()) if oldest else 0

        violations.append(
            Violation(
                project_uuid=project_uuid,
                metric=metric,
                violating_count=violating_count,
                max_value_seconds=max_age,
                threshold_seconds=threshold_seconds,
                rooms_threshold_count=threshold_count,
                rooms_threshold_percent=goal["rooms_threshold_percent"],
                active_rooms_count=active_count,
                email_enabled=bool(goal.get("email_enabled", False)),
                detected_at=now,
            )
        )

    return violations


def _state_key(project_uuid: str, metric: str) -> str:
    return STATE_KEY_TEMPLATE.format(project_uuid=project_uuid, metric=metric)


def _alert_state_key(project_uuid: str, metric: str) -> str:
    return ALERT_STATE_KEY_TEMPLATE.format(
        project_uuid=project_uuid, metric=metric
    )


def _claim_key(redis_conn, key: str, value: str, ttl_seconds: int) -> bool:
    """SET NX + refresh TTL. Returns True when the key was newly created."""
    was_set = redis_conn.set(key, value, nx=True, ex=ttl_seconds)
    if was_set:
        return True
    redis_conn.expire(key, ttl_seconds)
    return False


def _claim_state(
    redis_conn, project_uuid: str, metric: str, ttl_seconds: int
) -> bool:
    """Mark (project, metric) as violating (any room in breach)."""
    return _claim_key(
        redis_conn, _state_key(project_uuid, metric), STATE_VIOLATING, ttl_seconds
    )


def _claim_alert_state(
    redis_conn, project_uuid: str, metric: str, ttl_seconds: int
) -> bool:
    """Mark (project, metric) as above the rooms threshold for toast/email."""
    return _claim_key(
        redis_conn,
        _alert_state_key(project_uuid, metric),
        STATE_ALERTING,
        ttl_seconds,
    )


def _clear_state(redis_conn, project_uuid: str, metric: str) -> bool:
    """Remove the violating state key."""
    return bool(redis_conn.delete(_state_key(project_uuid, metric)))


def _clear_alert_state(redis_conn, project_uuid: str, metric: str) -> bool:
    """Remove the toast/email alerting state key."""
    return bool(redis_conn.delete(_alert_state_key(project_uuid, metric)))


def _keys_for_metric(redis_conn, template: str, metric: str) -> Set[str]:
    """List ``project_uuid`` values currently flagged for ``template``."""
    pattern = template.format(project_uuid="*", metric=metric)
    project_uuids: Set[str] = set()
    for raw in redis_conn.scan_iter(match=pattern):
        key = raw.decode() if isinstance(raw, bytes) else raw
        try:
            project_uuid = key.split(":")[1]
        except IndexError:
            continue
        project_uuids.add(project_uuid)
    return project_uuids


def _violating_keys_for_metric(redis_conn, metric: str) -> Set[str]:
    """List ``project_uuid`` values currently flagged as violating."""
    return _keys_for_metric(redis_conn, STATE_KEY_TEMPLATE, metric)


def _alerting_keys_for_metric(redis_conn, metric: str) -> Set[str]:
    """List ``project_uuid`` values currently flagged for toast/email."""
    return _keys_for_metric(redis_conn, ALERT_STATE_KEY_TEMPLATE, metric)


@dataclass(frozen=True)
class ProcessingResult:
    metric: str
    new_alerts: List[Violation]
    updates: List[Violation]
    resolved: List[str]
    toasts: List[Violation] = field(default_factory=list)


def _safe_call(
    callback,
    label: str,
    project_uuid: str,
    metric: str,
    *args,
) -> bool:
    """Invoke ``callback`` when provided, logging failures.

    Returns ``True`` only when the callback ran without raising. ``False``
    when the callback is ``None`` or when it raised an exception.
    """
    if callback is None:
        return False
    try:
        callback(*args)
        return True
    except Exception:  # noqa: BLE001
        logger.exception(label, project_uuid, metric)
        return False


def process_violations(
    metric: str,
    *,
    state_ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS,
    on_new_alert=None,
    on_update=None,
    on_resolved=None,
    on_toast=None,
    on_email=None,
    now: datetime | None = None,
    # Kept for call-site compatibility; rearm-by-threshold replaced cooldown.
    email_cooldown_seconds: int | None = None,
) -> ProcessingResult:
    """Detect violations and reconcile with the Redis state machines.

    Widget path (``on_new_alert`` / ``on_update`` / ``on_resolved``):
    claimed as soon as any room breaches ``threshold_seconds``.

    Toast/email path (``on_toast`` / ``on_email``): claimed only when
    ``email_enabled`` and ``violating_count >= rooms_threshold_count``.
    Dropping below that count clears toast state so a later climb back
    fires toast/email again.

    The callbacks are intentionally optional so the service can be
    exercised in tests without the Celery/Channels stack. Real callers
    (see ``chats.apps.dashboard.tasks``) wire them to broadcast helpers.
    """
    del email_cooldown_seconds  # unused; kept for backwards-compatible kwargs

    violations = detect_violations(metric, now=now)
    redis_conn = get_redis_connection()

    previously_violating = _violating_keys_for_metric(redis_conn, metric)
    previously_alerting = _alerting_keys_for_metric(redis_conn, metric)
    currently_violating: Set[str] = set()
    currently_alerting: Set[str] = set()

    new_alerts: List[Violation] = []
    updates: List[Violation] = []
    toasts: List[Violation] = []
    emails_sent: List[Violation] = []

    for violation in violations:
        currently_violating.add(violation.project_uuid)
        is_new = _claim_state(
            redis_conn, violation.project_uuid, metric, state_ttl_seconds
        )

        if is_new:
            new_alerts.append(violation)
            _safe_call(
                on_new_alert,
                "metric_goal: on_new_alert failed (project=%s metric=%s)",
                violation.project_uuid,
                metric,
                violation,
            )
        else:
            updates.append(violation)
            _safe_call(
                on_update,
                "metric_goal: on_update failed (project=%s metric=%s)",
                violation.project_uuid,
                metric,
                violation,
            )

        if not violation.email_enabled or not violation.meets_rooms_threshold:
            continue

        currently_alerting.add(violation.project_uuid)
        is_new_toast = _claim_alert_state(
            redis_conn, violation.project_uuid, metric, state_ttl_seconds
        )
        if not is_new_toast:
            continue

        toasts.append(violation)
        _safe_call(
            on_toast,
            "metric_goal: on_toast failed (project=%s metric=%s)",
            violation.project_uuid,
            metric,
            violation,
        )
        if _safe_call(
            on_email,
            "metric_goal: on_email failed (project=%s metric=%s)",
            violation.project_uuid,
            metric,
            violation,
        ):
            emails_sent.append(violation)

    resolved_uuids = list(previously_violating - currently_violating)
    for project_uuid in resolved_uuids:
        _clear_state(redis_conn, project_uuid, metric)
        _clear_alert_state(redis_conn, project_uuid, metric)
        _safe_call(
            on_resolved,
            "metric_goal: on_resolved failed (project=%s metric=%s)",
            project_uuid,
            metric,
            project_uuid,
            metric,
        )

    # Dropped below rooms threshold but still violating: clear toast state
    # so the next climb re-fires toast/email without a widget resolve.
    for project_uuid in previously_alerting - currently_alerting:
        if project_uuid in currently_violating:
            _clear_alert_state(redis_conn, project_uuid, metric)

    logger.info(
        "metric_goal sweep: metric=%s new=%s updates=%s resolved=%s "
        "toasts=%s emails=%s",
        metric,
        len(new_alerts),
        len(updates),
        len(resolved_uuids),
        len(toasts),
        len(emails_sent),
    )

    return ProcessingResult(
        metric=metric,
        new_alerts=new_alerts,
        updates=updates,
        resolved=resolved_uuids,
        toasts=toasts,
    )
