from rest_framework import serializers

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import QueueAuthorization


class ChatsLimitSerializer(serializers.Serializer):
    active = serializers.BooleanField(source="is_custom_limit_active")
    total = serializers.IntegerField(source="custom_rooms_limit", allow_null=True)


# ---------------------------------------------------------------------------
# ENGAGE-7672 — GET /v1/project/{uuid}/all_agents
# ---------------------------------------------------------------------------


class AllAgentsAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPermission
        fields = []

    def _build_sectors(self, permission):
        sectors_by_uuid = {}

        for sector_auth in permission.sector_authorizations.all():
            sector = sector_auth.sector
            if sector.pk not in sectors_by_uuid:
                sectors_by_uuid[sector.pk] = {"sector": sector, "queue_names": set()}

        for queue_auth in permission.queue_authorizations.all():
            sector = queue_auth.queue.sector
            if sector.pk not in sectors_by_uuid:
                sectors_by_uuid[sector.pk] = {"sector": sector, "queue_names": set()}
            sectors_by_uuid[sector.pk]["queue_names"].add(queue_auth.queue.name)

        return sectors_by_uuid

    def to_representation(self, obj):
        user = obj.user
        name = f"{user.first_name} {user.last_name}".strip() if user else ""

        sectors_by_uuid = self._build_sectors(obj)

        return {
            "name": name,
            "chats_limit": ChatsLimitSerializer(obj).data,
            "email": user.email if user else "",
            "sector": [
                {
                    "name": entry["sector"].name,
                    "queues": sorted(entry["queue_names"]),
                }
                for entry in sectors_by_uuid.values()
            ],
            "sector_chats_total_limit": sum(
                entry["sector"].rooms_limit for entry in sectors_by_uuid.values()
            ),
        }


class AllAgentsSerializer(serializers.ModelSerializer):
    agent = AllAgentsAgentSerializer(source="*")

    class Meta:
        model = ProjectPermission
        fields = ["agent"]


# ---------------------------------------------------------------------------
# ENGAGE-7558 — GET /v1/agent/queue_permissions/
# ---------------------------------------------------------------------------


class AgentQueuePermissionsSerializer(serializers.Serializer):
    chats_limit = serializers.SerializerMethodField()
    queue_permissions = serializers.SerializerMethodField()

    def get_chats_limit(self, obj):
        return ChatsLimitSerializer(obj["permission"]).data

    def get_queue_permissions(self, obj):
        permission = obj["permission"]
        sectors_data = obj["sectors_data"]

        agent_queue_ids = set(
            QueueAuthorization.objects.filter(permission=permission).values_list(
                "queue_id", flat=True
            )
        )

        result = []
        for sector in sectors_data:
            queues = [
                {
                    "uuid": str(queue.pk),
                    "name": queue.name,
                    "agent_in_queue": queue.pk in agent_queue_ids,
                }
                for queue in sector.queues.filter(is_deleted=False)
            ]
            result.append({"sector": {"name": sector.name, "queues": queues}})
        return result


# ---------------------------------------------------------------------------
# ENGAGE-7557 — POST /v1/agent/update_queue_permissions/
# ---------------------------------------------------------------------------


class ChatsLimitInputSerializer(serializers.Serializer):
    active = serializers.BooleanField(required=False, default=False)
    total = serializers.IntegerField(required=False, allow_null=True, default=None)


class UpdateQueuePermissionsSerializer(serializers.Serializer):
    agents = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
    )
    to_add = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    to_remove = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    chats_limit = ChatsLimitInputSerializer(required=False, default=None)
    project = serializers.UUIDField()

    def validate(self, attrs):
        if (
            not attrs.get("to_add")
            and not attrs.get("to_remove")
            and attrs.get("chats_limit") is None
        ):
            raise serializers.ValidationError(
                "At least one of to_add, to_remove or chats_limit must be provided."
            )
        return attrs
