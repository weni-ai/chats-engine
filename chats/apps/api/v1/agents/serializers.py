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
    name = serializers.SerializerMethodField()
    chats_limit = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPermission
        fields = ["name", "chats_limit"]

    def get_name(self, obj):
        user = obj.user
        if not user:
            return ""
        return f"{user.first_name} {user.last_name}".strip()

    def get_chats_limit(self, obj):
        return ChatsLimitSerializer(obj).data


class AllAgentsSerializer(serializers.ModelSerializer):
    agent = AllAgentsAgentSerializer(source="*")
    email = serializers.EmailField(source="user.email")
    sector_auth = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPermission
        fields = ["agent", "email", "sector_auth"]

    def get_sector_auth(self, obj):
        sectors = obj.get_sectors()
        return list(sectors.values_list("name", flat=True))


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
