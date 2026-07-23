from typing import Optional
from django.utils import timezone
from rest_framework import serializers
from django.utils import timezone

from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.csat.models import CSATSurvey
from chats.apps.rooms.models import Room
from chats.apps.dashboard.models import MetricGoal, RoomMetrics

# Maps each MetricGoal metric to the serializer method used to compute the
# equivalent per-room value, so `goals_metrics` can reuse the exact same
# figures already shown in `duration` / `queue_time` / `first_response_time`.
# Waiting-time goals mirror MetricGoalBreachService: for rooms still in the
# queue they compare against `queue_time` (now - added_to_queue_at), not
# RoomMetrics.waiting_time (which stays 0 until an agent is assigned).
_GOAL_METRIC_TO_OUTPUT_KEY = {
    MetricGoal.METRIC_WAITING_TIME: "awaiting_time",
    MetricGoal.METRIC_FIRST_RESPONSE_TIME: "first_response_time",
    MetricGoal.METRIC_CONVERSATION_DURATION: "duration",
}


class RoomInternalListSerializer(serializers.ModelSerializer):
    contact = serializers.SerializerMethodField()
    agent = serializers.SerializerMethodField()
    user_email = serializers.EmailField(
        source="user.email", default=None, read_only=True
    )
    tags = TagSimpleSerializer(many=True, required=False)
    sector = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    first_response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()
    queue_time = serializers.SerializerMethodField()
    csat_rating = serializers.SerializerMethodField()
    pending_response = serializers.BooleanField(read_only=True, default=False)
    goals_metrics = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "agent",
            "user_email",
            "contact",
            "urn",
            "is_active",
            "ended_at",
            "sector",
            "queue",
            "created_on",
            "tags",
            "link",
            "duration",
            "first_response_time",
            "waiting_time",
            "queue_time",
            "csat_rating",
            "pending_response",
            "protocol",
            "goals_metrics",
        ]

    def _clean_soft_deleted_name(self, name: str) -> str:
        if "_is_deleted_" in name:
            return name.split("_is_deleted_")[0]
        return name

    def get_sector(self, obj) -> str:
        try:
            return self._clean_soft_deleted_name(obj.queue.sector.name)
        except AttributeError:
            return ""

    def get_queue(self, obj) -> str:
        try:
            return self._clean_soft_deleted_name(obj.queue.name)
        except AttributeError:
            return ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.context.get("include_pending_response", False):
            self.fields.pop("pending_response", None)

    def get_contact(self, obj) -> str:
        try:
            return obj.contact.name if obj.contact else ""
        except AttributeError:
            return ""

    def get_agent(self, obj):
        try:
            return obj.user.full_name
        except AttributeError:
            return ""

    def get_link(self, obj: Room) -> dict:
        if obj.user and obj.is_active:
            url = f"chats:dashboard/view-mode/{obj.user.email}?uuid_room={obj.uuid}"
        elif not obj.user and obj.is_active:
            url = f"chats:chats/{obj.uuid}"
        elif not obj.is_active:
            url = f"chats:closed-chats/{obj.uuid}"
        else:
            url = None

        return {
            "url": url,
            "type": "internal",
        }

    def get_duration(self, obj: Room) -> int:
        if not obj.first_user_assigned_at:
            return None
        if obj.is_active and obj.user:
            return int((timezone.now() - obj.first_user_assigned_at).total_seconds())
        elif not obj.is_active and obj.ended_at:
            return int((obj.ended_at - obj.first_user_assigned_at).total_seconds())
        return None

    def get_first_response_time(self, obj: Room) -> int:
        try:
            metrics: Optional[RoomMetrics] = getattr(obj, "metric", None)

            if metrics and metrics.first_response_time is not None:
                return metrics.first_response_time

            if not obj.is_active and (
                not metrics or metrics.first_response_time is None
            ):
                return None

            if obj.first_user_assigned_at and obj.is_active and obj.user:
                has_any_agent_messages = (
                    obj.messages.filter(user__isnull=False)
                    .exclude(automatic_message__isnull=False)
                    .exists()
                )

                if has_any_agent_messages:
                    return 0

                return int(
                    (timezone.now() - obj.first_user_assigned_at).total_seconds()
                )
        except Exception:
            pass
        return 0

    def get_waiting_time(self, obj: Room) -> int:
        metrics = getattr(obj, "metric", None)

        if not metrics:
            return 0

        return metrics.waiting_time

    def get_queue_time(self, obj: Room) -> int:
        if obj.is_active and not obj.user:
            queue_start = obj.added_to_queue_at
            return int((timezone.now() - queue_start).total_seconds())
        return 0

    def get_csat_rating(self, obj: Room) -> int:
        csat_survey: Optional[CSATSurvey] = getattr(obj, "csat_survey", None)

        if csat_survey:
            return csat_survey.rating

        return None

    def get_goals_metrics(self, obj: Room) -> dict:
        """Per-room breach flags for each metric with an active goal.

        Mirrors the aggregate `{metric}_goal` payload exposed by
        `time_metrics/`, but evaluated for this single room instead of the
        whole project. A metric key is only included when the project has
        an active `MetricGoal` configured for it.
        """
        goals_by_metric = self.context.get("active_goals_by_metric") or {}
        if not goals_by_metric:
            return {}

        value_getters = {
            MetricGoal.METRIC_WAITING_TIME: self.get_queue_time,
            MetricGoal.METRIC_FIRST_RESPONSE_TIME: self.get_first_response_time,
            MetricGoal.METRIC_CONVERSATION_DURATION: self.get_duration,
        }

        goals_metrics = {}
        for metric, goal in goals_by_metric.items():
            output_key = _GOAL_METRIC_TO_OUTPUT_KEY.get(metric)
            getter = value_getters.get(metric)
            if not output_key or not getter:
                continue

            value = getter(obj) or 0
            goals_metrics[output_key] = {
                "exceeded": value >= goal.threshold_seconds,
            }

        return goals_metrics


class InternalProtocolRoomsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["protocol"]
