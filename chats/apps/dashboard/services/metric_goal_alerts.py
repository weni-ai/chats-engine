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

``rooms_threshold_count`` / ``rooms_threshold_percent`` only gate the
*email* notification. The WebSocket/toast alert (and the widget state)
fires as soon as a single room breaches ``threshold_seconds`` — per the
product epic, the "how many rooms" configuration is specific to the
email channel, since email is opt-in and independent from the
real-time alert.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import ceil
from typing import Iterable

from django.conf import settings
from django.db.models import Count, Exists, Max, OuterRef
from django.utils import timezone
from django_redis import get_redis_connection
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.dashboard.models import MetricGoal, RoomMetrics
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


def is_metric_goal_alerts_enabled(project_uuid: str) -> bool:
    """Whether the metric goal / risk alerts feature is enabled for a project.

    Fails closed (returns ``False``) if the flag can't be evaluated, so a
    GrowthBook outage never turns on alerts for projects that shouldn't
    have them.
    """
    if not project_uuid:
        return False
    try:
        return is_feature_active_for_attributes(
            settings.METRIC_GOAL_ALERTS_FEATURE_FLAG_KEY,
            {"projectUUID": str(project_uuid)},
        )
    except Exception:
        logger.warning(
            "metric_goal: failed to evaluate feature flag for project %s",
            project_uuid,
            exc_info=True,
        )
        return False


STATE_VIOLATING = "violating"

DEFAULT_STATE_TTL_SECONDS = 30 * 60
DEFAULT_EMAIL_COOLDOWN_SECONDS = 15 * 60

STATE_KEY_TEMPLATE = "metric_goal_state:{project_uuid}:{metric}"
EMAIL_COOLDOWN_KEY_TEMPLATE = "metric_goal_email_sent:{project_uuid}:{metric}"


TRANSITION_NEW = "new"
TRANSITION_UPDATE = "update"
TRANSITION_RESOLVED = "resolved"


@dataclass(frozen=True)
class Violation:
    """A project currently in breach of a metric goal.

    ``violating_count`` is the real-time count of rooms in breach and is
    what drives the WebSocket/toast/widget alert — that alert fires as
    soon as ``violating_count >= 1``. ``rooms_threshold_count`` /
    ``rooms_threshold_percent`` are only used to decide whether the
    *email* notification should also be sent (see ``meets_email_threshold``).
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
    def meets_email_threshold(self) -> bool:
        """Whether enough rooms are in breach to justify sending an email."""
        return self.violating_count >= self.rooms_threshold_count

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
        return base.filter(
            first_user_assigned_at__isnull=False,
            first_user_assigned_at__lte=cutoff,
        )

    raise ValueError(f"Unknown metric: {metric}")


def _max_age_field(metric: str) -> str:
    if metric == MetricGoal.METRIC_WAITING_TIME:
        return "added_to_queue_at"
    return "first_user_assigned_at"


def _resolve_threshold_count(
    goal_data: dict, active_rooms_count: int | None
) -> int:
    percent = goal_data.get("rooms_threshold_percent")
    if percent and active_rooms_count is not None:
        return max(1, ceil(active_rooms_count * percent / 100))
    return goal_data.get("rooms_threshold_count") or (
        MetricGoal.DEFAULT_ROOMS_THRESHOLD_COUNT
    )


def _project_active_room_counts(project_uuids: Iterable[str]) -> dict[str, int]:
    if not project_uuids:
        return {}
    rows = (
        Room.objects.filter(
            queue__sector__project__uuid__in=list(project_uuids), is_active=True
        )
        .values("queue__sector__project__uuid")
        .annotate(count=Count("uuid"))
    )
    return {
        str(row["queue__sector__project__uuid"]): row["count"] for row in rows
    }


def detect_violations(
    metric: str, now: datetime | None = None
) -> list[Violation]:
    """Return the list of projects currently violating ``metric``.

    One small aggregate query is issued per configured ``MetricGoal``.
    With ~230 active projects this stays well within the planner's
    sweet spot and keeps query shapes index-friendly.
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
    violations: list[Violation] = []

    for goal in goals:
        project_uuid = str(goal["project__uuid"])
        threshold_seconds = goal["threshold_seconds"]
        cutoff = now - timedelta(seconds=threshold_seconds)

        qs = _build_violation_queryset(metric, project_uuid, cutoff)
        agg = qs.aggregate(count=Count("uuid"), oldest=Max(age_field))
        violating_count = agg["count"] or 0

        if violating_count == 0:
            continue

        # The WebSocket/toast/widget alert fires with a single room in
        # breach. `threshold_count` is only computed here to carry it
        # along on the Violation, so `process_violations` can later decide
        # whether the email threshold was also met.
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


def _email_cooldown_key(project_uuid: str, metric: str) -> str:
    return EMAIL_COOLDOWN_KEY_TEMPLATE.format(
        project_uuid=project_uuid, metric=metric
    )


def _claim_state(
    redis_conn, project_uuid: str, metric: str, ttl_seconds: int
) -> bool:
    """Attempt to mark the (project, metric) as violating.

    Returns ``True`` when this call transitioned the state from clean to
    violating (i.e. a fresh alert). Returns ``False`` when the state was
    already set, in which case we simply refresh the TTL.
    """
    key = _state_key(project_uuid, metric)
    was_set = redis_conn.set(key, STATE_VIOLATING, nx=True, ex=ttl_seconds)
    if was_set:
        return True
    redis_conn.expire(key, ttl_seconds)
    return False


def _clear_state(redis_conn, project_uuid: str, metric: str) -> bool:
    """Remove the state key. Returns ``True`` when something was cleared."""
    return bool(redis_conn.delete(_state_key(project_uuid, metric)))


def _claim_email_slot(
    redis_conn, project_uuid: str, metric: str, ttl_seconds: int
) -> bool:
    """Reserve the email cooldown slot. Returns ``True`` if newly claimed."""
    key = _email_cooldown_key(project_uuid, metric)
    return bool(redis_conn.set(key, "1", nx=True, ex=ttl_seconds))


def _violating_keys_for_metric(redis_conn, metric: str) -> set[str]:
    """List ``project_uuid`` values currently flagged as violating."""
    pattern = STATE_KEY_TEMPLATE.format(project_uuid="*", metric=metric)
    project_uuids: set[str] = set()
    for raw in redis_conn.scan_iter(match=pattern):
        key = raw.decode() if isinstance(raw, bytes) else raw
        try:
            project_uuid = key.split(":")[1]
        except IndexError:
            continue
        project_uuids.add(project_uuid)
    return project_uuids


@dataclass(frozen=True)
class ProcessingResult:
    metric: str
    new_alerts: list[Violation]
    updates: list[Violation]
    resolved: list[str]


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
    email_cooldown_seconds: int = DEFAULT_EMAIL_COOLDOWN_SECONDS,
    on_new_alert=None,
    on_update=None,
    on_resolved=None,
    on_email=None,
    now: datetime | None = None,
) -> ProcessingResult:
    """Detect violations and reconcile with the Redis state machine.

    The callbacks are intentionally optional so the service can be
    exercised in tests without the Celery/Channels stack. Real callers
    (see ``chats.apps.dashboard.tasks``) wire them to broadcast helpers.
    """
    violations = detect_violations(metric, now=now)
    redis_conn = get_redis_connection()

    previously_violating = _violating_keys_for_metric(redis_conn, metric)
    currently_violating: set[str] = set()

    new_alerts: list[Violation] = []
    updates: list[Violation] = []
    emails_sent: list[Violation] = []

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

        # Email is gated by rooms_threshold_count ("Quando"), which may be
        # crossed on the first breach (new) or only later (update). The
        # cooldown slot ensures we still send at most once per metric
        # until the TTL expires.
        if (
            on_email is not None
            and violation.email_enabled
            and violation.meets_email_threshold
            and _claim_email_slot(
                redis_conn,
                violation.project_uuid,
                metric,
                email_cooldown_seconds,
            )
            and _safe_call(
                on_email,
                "metric_goal: on_email failed (project=%s metric=%s)",
                violation.project_uuid,
                metric,
                violation,
            )
        ):
            emails_sent.append(violation)

    resolved_uuids = list(previously_violating - currently_violating)
    for project_uuid in resolved_uuids:
        _clear_state(redis_conn, project_uuid, metric)
        _safe_call(
            on_resolved,
            "metric_goal: on_resolved failed (project=%s metric=%s)",
            project_uuid,
            metric,
            project_uuid,
            metric,
        )

    logger.info(
        "metric_goal sweep: metric=%s new=%s updates=%s resolved=%s emails=%s",
        metric,
        len(new_alerts),
        len(updates),
        len(resolved_uuids),
        len(emails_sent),
    )

    return ProcessingResult(
        metric=metric,
        new_alerts=new_alerts,
        updates=updates,
        resolved=resolved_uuids,
    )
