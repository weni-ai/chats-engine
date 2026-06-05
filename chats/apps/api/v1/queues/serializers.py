from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from weni.feature_flags.shortcuts import is_feature_active

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector
from chats.core.serializers import AuditableModelSerializer

User = get_user_model()

MAX_INT_32 = 2**31 - 1


class QueueLimitSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=MAX_INT_32
    )
    is_active = serializers.BooleanField(required=False, allow_null=True)

    def validate(self, data):
        if data.get("is_active") is True and data.get("limit") is None:
            raise serializers.ValidationError(
                {"limit": _("Limit is required when queue limit is active.")}
            )
        return data


class QueueSerializer(AuditableModelSerializer):

    sector_name = serializers.CharField(source="sector.name", read_only=True)
    required_tags = serializers.BooleanField(
        source="sector.required_tags", read_only=True
    )
    queue_limit = QueueLimitSerializer(required=False, source="queue_limit_info")

    class Meta:
        model = Queue
        fields = [
            "uuid",
            "sector_name",
            "required_tags",
            "queue_limit",
            "created_on",
            "modified_on",
            "is_deleted",
            "config",
            "name",
            "sector",
        ]

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.sector.project
        sector = (self.validated_data or {}).get("sector")
        return sector.project if sector else None

    def validate(self, data):
        """
        Check if queue already exist in sector.
        """
        name = data.get("name")
        if name:
            if name == "":
                raise serializers.ValidationError(
                    {"detail": _("The name field can't be blank.")}
                )
            if self.instance:
                if Queue.objects.filter(
                    sector=self.instance.sector, name=name
                ).exists():
                    raise serializers.ValidationError(
                        {"detail": _("This queue already exists.")}
                    )
            else:
                if Queue.objects.filter(sector=data["sector"], name=name).exists():
                    raise serializers.ValidationError(
                        {"detail": _("This queue already exists.")}
                    )

        queue_limit = data.pop("queue_limit_info", None)

        if queue_limit and isinstance(queue_limit, dict):
            if "is_active" in queue_limit:
                data["is_queue_limit_active"] = queue_limit.get("is_active")

            if "limit" in queue_limit:
                data["queue_limit"] = queue_limit.get("limit")

        return data


class QueueSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = ["uuid", "name"]


class QueueUpdateSerializer(AuditableModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    sector_uuid = serializers.CharField(source="sector.uuid", read_only=True)
    queue_limit = QueueLimitSerializer(source="queue_limit_info")

    class Meta:
        model = Queue
        fields = [
            "uuid",
            "name",
            "agents",
            "created_on",
            "sector_name",
            "sector_uuid",
            "required_tags",
            "queue_limit",
        ]

    def get_agents(self, queue: Queue):
        return queue.agent_count


class QueueAuthorizationSerializer(AuditableModelSerializer):
    queue_name = serializers.CharField(source="queue.name", read_only=True)

    class Meta:
        model = QueueAuthorization
        fields = "__all__"

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.queue.sector.project
        queue = (self.validated_data or {}).get("queue")
        return queue.sector.project if queue else None

    def validate(self, data):
        """
        Check if user already exist in queue.
        """
        queue_user = QueueAuthorization.objects.filter(
            permission=data["permission"], queue=data["queue"]
        )
        if queue_user:
            raise serializers.ValidationError(
                {"detail": _("you cant add a user two times in same queue.")}
            )
        return data


class QueueAuthorizationUpdateSerializer(AuditableModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueAuthorizationReadOnlyListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = QueueAuthorization
        fields = [
            "uuid",
            "queue",
            "role",
            "user",
        ]

    def get_user(self, auth):
        return UserSerializer(auth.permission.user).data


class QueueAgentsSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "status",
            "first_name",
            "last_name",
            "email",
            "photo_url",
            "language",
        ]

    def get_status(self, obj):
        pause_name = getattr(obj, "_pause_name", None)
        if pause_name:
            return pause_name

        is_online = getattr(obj, "_is_online", None)
        if is_online is not None:
            return "online" if is_online else "offline"

        project = self.context.get("project")
        if not project:
            return "offline"

        from chats.apps.projects.models.models import CustomStatus

        active_pause = (
            CustomStatus.objects.filter(
                user=obj, project=project, is_active=True
            )
            .exclude(status_type__name__iexact="in-service")
            .select_related("status_type")
            .first()
        )
        if active_pause:
            return active_pause.status_type.name

        project_permission = obj.project_permissions.filter(project=project).first()
        if project_permission and project_permission.status == "ONLINE":
            return "online"
        return "offline"


class QueuePermissionsListQueryParamsSerializer(serializers.Serializer):
    user_email = serializers.EmailField()
    project = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data: dict) -> dict:
        project = data.get("project")

        if project is None or project == "":
            data.pop("project")

        return data


class BulkQueueItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    config = serializers.JSONField(required=False, allow_null=True)
    queue_limit = QueueLimitSerializer(required=False, allow_null=True)
    agents = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list,
    )


class BulkQueueCreateSerializer(serializers.Serializer):
    sector = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.filter(is_deleted=False),
        pk_field=serializers.UUIDField(format="hex_verbose"),
    )
    queues = BulkQueueItemSerializer(many=True)

    def validate(self, data):
        sector = data["sector"]
        queues = data["queues"]

        request = self.context.get("request")
        if request and not is_feature_active(
            settings.QUEUE_BULK_CREATE_FEATURE_FLAG_KEY,
            request.user.email,
            str(sector.project.uuid),
        ):
            raise serializers.ValidationError(
                {"detail": _("Bulk queue create feature is not active.")},
                code="bulk_queue_create_feature_flag_is_off",
            )

        if not queues:
            raise serializers.ValidationError(
                {"queues": _("At least one queue is required.")}
            )

        max_items = settings.QUEUE_BULK_CREATE_MAX_ITEMS
        if len(queues) > max_items:
            raise serializers.ValidationError(
                {
                    "queues": _(
                        "A maximum of %(max)d queues can be created per request."
                    )
                    % {"max": max_items}
                }
            )

        queue_names = [queue_data["name"] for queue_data in queues]

        if len(queue_names) != len(set(queue_names)):
            raise serializers.ValidationError(
                {"queues": _("There are duplicate queue names in the request.")}
            )

        existing_names = list(
            Queue.objects.filter(sector=sector, name__in=queue_names).values_list(
                "name", flat=True
            )
        )
        if existing_names:
            raise serializers.ValidationError(
                {
                    "queues": f"{_('Queue(s) already exist in this sector')}: {', '.join(existing_names)}."
                }
            )

        if request:
            is_queue_limit_feature_active = is_feature_active(
                settings.QUEUE_LIMIT_FEATURE_FLAG_KEY,
                request.user.email,
                str(sector.project.uuid),
            )
            for queue_data in queues:
                queue_limit = queue_data.get("queue_limit")
                if (
                    queue_limit
                    and not is_queue_limit_feature_active
                    and queue_limit.get("is_active") is True
                ):
                    raise serializers.ValidationError(
                        {"detail": _("Queue limit feature is not active.")},
                        code="queue_limit_feature_flag_is_off",
                    )

        return data
