"""
Services for the metric goals feature.

`MetricGoalBreachService` is the single source of truth for "is this goal
currently being breached?". It is consumed today by the `time_metrics`
endpoint (so the front can render widget alerts) and will be consumed
later by the periodic detection task that emits real-time notifications.
Keeping the breach logic in one place avoids drift between the two
consumers.
"""

from datetime import timedelta
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.metric_goals.constants import (
    threshold_seconds_to_unit_value,
)
from chats.apps.dashboard.models import MetricGoal
from chats.apps.rooms.models import Room


def _apply_filters_to_q(base_filter: Q, filters: Optional[Filters]) -> Q:
    """
    Mirrors the request-scoped filtering used by `TimeMetricsService` so
    the breach count respects the same scope (sector, queue, tag, agent)
    that the user sees on the dashboard.
    """
    if filters is None:
        return base_filter

    if filters.sector:
        base_filter &= Q(queue__sector__in=filters.sector)
        if filters.tag:
            base_filter &= Q(tags__uuid__in=filters.tag)
    if filters.queue:
        base_filter &= Q(queue__uuid__in=filters.queue)
    if filters.agent:
        base_filter &= Q(user=filters.agent)
    return base_filter


class MetricGoalBreachService:
    """
    Computes the breach state for a project's metric goals.

    The service returns one entry per active goal, omitting metrics that
    do not have a goal configured or whose goal is inactive. Each entry
    follows the contract agreed with the front:

        {
            "threshold_seconds": int,
            "threshold_value": int,
            "unit": "s" | "m" | "h",
            "is_breached": bool,
            "breached_rooms_count": int,
        }

    Goals are flagged as breached as soon as a single room is above the
    threshold. `rooms_threshold_count` / `rooms_threshold_percent` do not
    gate this widget alert — they only gate the email notification (see
    `chats.apps.dashboard.services.metric_goal_alerts.Violation.meets_email_threshold`),
    since email is opt-in and independent from the real-time alert.
    """

    def get_goals_payload(
        self, project, filters: Optional[Filters] = None
    ) -> dict:
        """Returns `{metric}_goal` entries keyed by metric name."""
        goals = MetricGoal.objects.filter(
            project=project,
            is_active=True,
        )

        return {
            f"{goal.metric}_goal": self._build_goal_entry(goal, filters)
            for goal in goals
        }

    def _build_goal_entry(
        self, goal: MetricGoal, filters: Optional[Filters]
    ) -> dict:
        breached_count = self._count_breached_rooms(goal, filters)
        return {
            "threshold_seconds": goal.threshold_seconds,
            "threshold_value": threshold_seconds_to_unit_value(
                goal.threshold_seconds, goal.unit
            ),
            "unit": goal.unit,
            "is_breached": breached_count >= 1,
            "breached_rooms_count": breached_count,
        }

    def _count_breached_rooms(
        self, goal: MetricGoal, filters: Optional[Filters]
    ) -> int:
        if goal.metric == MetricGoal.METRIC_WAITING_TIME:
            return self._count_waiting_time_breaches(goal, filters)
        if goal.metric == MetricGoal.METRIC_FIRST_RESPONSE_TIME:
            return self._count_first_response_time_breaches(goal, filters)
        if goal.metric == MetricGoal.METRIC_CONVERSATION_DURATION:
            return self._count_conversation_duration_breaches(goal, filters)
        return 0

    def _count_waiting_time_breaches(
        self, goal: MetricGoal, filters: Optional[Filters]
    ) -> int:
        threshold_cutoff = timezone.now() - timedelta(
            seconds=goal.threshold_seconds
        )
        base_filter = Q(
            queue__sector__project=goal.project,
            is_active=True,
            user__isnull=True,
            added_to_queue_at__isnull=False,
            added_to_queue_at__lte=threshold_cutoff,
        )
        base_filter = _apply_filters_to_q(base_filter, filters)
        return Room.objects.filter(base_filter).count()

    def _count_first_response_time_breaches(
        self, goal: MetricGoal, filters: Optional[Filters]
    ) -> int:
        threshold_cutoff = timezone.now() - timedelta(
            seconds=goal.threshold_seconds
        )
        no_response_yet = (
            Q(metric__isnull=True)
            | Q(metric__first_response_time=0)
            | Q(metric__first_response_time__isnull=True)
        )
        base_filter = Q(
            queue__sector__project=goal.project,
            is_active=True,
            user__isnull=False,
            first_user_assigned_at__isnull=False,
            first_user_assigned_at__lte=threshold_cutoff,
        ) & no_response_yet
        base_filter = _apply_filters_to_q(base_filter, filters)
        return Room.objects.filter(base_filter).count()

    def _count_conversation_duration_breaches(
        self, goal: MetricGoal, filters: Optional[Filters]
    ) -> int:
        threshold_cutoff = timezone.now() - timedelta(
            seconds=goal.threshold_seconds
        )
        base_filter = Q(
            queue__sector__project=goal.project,
            is_active=True,
            user__isnull=False,
            first_user_assigned_at__isnull=False,
            first_user_assigned_at__lte=threshold_cutoff,
        )
        base_filter = _apply_filters_to_q(base_filter, filters)
        return Room.objects.filter(base_filter).count()
