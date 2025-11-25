from typing import Optional
from django.utils import timezone
from rest_framework import serializers
from django.utils import timezone

from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.csat.models import CSATSurvey
from chats.apps.rooms.models import Room


class RoomInternalListSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="contact.name")
    agent = serializers.SerializerMethodField()
    tags = TagSimpleSerializer(many=True, required=False)
    sector = serializers.CharField(source="queue.sector.name")
    queue = serializers.CharField(source="queue.name")
    link = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    first_response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()
    queue_time = serializers.SerializerMethodField()
    csat_rating = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "agent",
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
            "protocol",
            "csat_rating",
        ]

    def get_agent(self, obj):
        try:
            return obj.user.full_name
        except AttributeError:
            return ""

    def get_link(self, obj: Room) -> dict:
        if obj.user and obj.is_active:
            url = f"chats:dashboard/view-mode/{obj.user.email}"
        elif not obj.user and obj.is_active:
            url = f"chats:chats/{obj.uuid}"
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
            if hasattr(obj, "metric") and obj.metric.first_response_time is not None:
                return obj.metric.first_response_time

            if obj.first_user_assigned_at and obj.is_active and obj.user:
                has_any_agent_messages = (
                    obj.messages.filter(user__isnull=False)
                    .exclude(automatic_message__isnull=False)
                    .exists()
                )

                if has_any_agent_messages:
                    return None

                return int(
                    (timezone.now() - obj.first_user_assigned_at).total_seconds()
                )
        except Exception:
            pass
        return None

    def get_waiting_time(self, obj: Room) -> int:
        if not obj.added_to_queue_at or not obj.user_assigned_at:
            return None
        return int((obj.user_assigned_at - obj.added_to_queue_at).total_seconds())

    def get_queue_time(self, obj: Room) -> int:
        if obj.is_active and not obj.user:
            queue_start = obj.added_to_queue_at
            return int((timezone.now() - queue_start).total_seconds())
        return None

    def get_csat_rating(self, obj: Room) -> int:
        csat_survey: Optional[CSATSurvey] = getattr(obj, "csat_survey", None)

        if csat_survey:
            return csat_survey.rating

        return None


class InternalProtocolRoomsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["protocol"]
