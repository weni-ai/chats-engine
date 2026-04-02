from typing import Optional

from django.utils import timezone
from rest_framework import serializers

from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.csat.models import CSATSurvey
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room


class RoomInternalListSerializerV2(serializers.ModelSerializer):
    contact = serializers.CharField(source="contact.name")
    agent = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", default=None, read_only=True)
    tags = TagSimpleSerializer(many=True, required=False)
    sector = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
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
            "protocol",
        ]

    def _agent_permission_is_deleted(self, obj: Room) -> bool:
        """
        True if there is no ProjectPermission for (agent, project) or it is soft-deleted.
        Project is room.queue.sector.project.
        """
        user = obj.user
        if not user or not obj.queue_id:
            return True
        queue = obj.queue
        if not queue or not queue.sector_id:
            return True
        project = queue.sector.project
        perm = ProjectPermission.all_objects.filter(user=user, project=project).first()
        return perm is None or perm.is_deleted

    def get_agent(self, obj: Room) -> Optional[dict]:
        user = obj.user
        if not user:
            return None

        try:
            name = user.full_name
        except AttributeError:
            name = ""

        return {
            "name": name,
            "email": user.email,
            "is_deleted": self._agent_permission_is_deleted(obj),
        }

    def get_sector(self, obj: Room) -> Optional[dict]:
        queue = obj.queue
        if not queue or not queue.sector_id:
            return None
        sector = queue.sector
        return {
            "name": sector.name,
            "is_deleted": sector.is_deleted,
        }

    def get_queue(self, obj: Room) -> Optional[dict]:
        queue = obj.queue
        if not queue:
            return None
        return {
            "name": queue.name,
            "is_deleted": queue.is_deleted,
        }

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
            return 0

        if obj.is_active and obj.user:
            return int((timezone.now() - obj.first_user_assigned_at).total_seconds())
        elif not obj.is_active and obj.ended_at:
            return int((obj.ended_at - obj.first_user_assigned_at).total_seconds())

        return 0

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
