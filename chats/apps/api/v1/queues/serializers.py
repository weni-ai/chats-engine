from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.queues.models import Queue, QueueAuthorization

User = get_user_model()


class QueueSerializer(serializers.ModelSerializer):

    sector_name = serializers.CharField(source="sector.name", read_only=True)
    required_tags = serializers.BooleanField(
        source="sector.required_tags", read_only=True
    )

    class Meta:
        model = Queue
        fields = "__all__"

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
        return data


class QueueSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = ["uuid", "name"]


class QueueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    sector_uuid = serializers.CharField(source="sector.uuid", read_only=True)

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
        ]

    def get_agents(self, queue: Queue):
        return queue.agent_count


class QueueAuthorizationSerializer(serializers.ModelSerializer):
    queue_name = serializers.CharField(source="queue.name", read_only=True)

    class Meta:
        model = QueueAuthorization
        fields = "__all__"

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


class QueueAuthorizationUpdateSerializer(serializers.ModelSerializer):
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
        project = self.context.get("project")
        if project:
            project_permission = obj.project_permissions.get(project=project)
            if project_permission.status == "ONLINE":
                return "online"
        return "offline"


class QueuePermissionsListQueryParamsSerializer(serializers.Serializer):
    user_email = serializers.EmailField()
    project = serializers.UUIDField(required=False, allow_null=True, allow_blank=True)

    def validate(self, data: dict) -> dict:
        project = data.get("project")

        if project is None or project == "":
            data.pop("project")

        return data