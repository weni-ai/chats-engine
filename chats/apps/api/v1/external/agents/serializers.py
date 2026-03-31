from django.utils import timezone
from pendulum.parser import parse as pendulum_parse
from rest_framework import serializers

from chats.apps.api.v1.internal.users.serializers import UserSerializer
from chats.apps.projects.models import ProjectPermission


class AgentFlowSerializer(serializers.ModelSerializer):
    """
    Serializer for agent (project permission) data via external API.

    Returns user information including email, first_name, last_name and photo_url.
    """

    user = UserSerializer(
        many=False,
        required=False,
        help_text="User data: email, first_name, last_name, photo_url",
    )

    class Meta:
        model = ProjectPermission
        fields = [
            "user",
        ]


class AgentStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for agent status monitoring via external API.

    Returns agent info, current status, last_seen, custom status (pause reason),
    last status change timestamp and time in current status (seconds).
    """

    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    photo_url = serializers.CharField(source="user.photo_url", default="")
    status = serializers.CharField()
    last_seen = serializers.DateTimeField()
    active_custom_status = serializers.SerializerMethodField()
    last_status_change = serializers.SerializerMethodField()
    time_in_current_status = serializers.SerializerMethodField()
    online_time = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPermission
        fields = [
            "uuid",
            "email",
            "first_name",
            "last_name",
            "photo_url",
            "status",
            "last_seen",
            "last_status_change",
            "time_in_current_status",
            "active_custom_status",
            "online_time",
        ]

    def get_active_custom_status(self, obj):
        name = getattr(obj, "_custom_status_name", None)
        if not name:
            return None
        return {
            "name": name,
            "since": getattr(obj, "_custom_status_since", None),
        }

    def get_last_status_change(self, obj):
        status_log_map = self.context.get("status_log_map", {})
        return status_log_map.get(obj.user.email)

    def get_time_in_current_status(self, obj):
        ts = self.get_last_status_change(obj)
        if not ts:
            return None
        last_dt = pendulum_parse(ts)
        return int((timezone.now() - last_dt).total_seconds())

    def get_online_time(self, obj):
        """Total online time in seconds for the requested date range."""
        online_time_map = self.context.get("online_time_map", {})
        return online_time_map.get(obj.user.email)
