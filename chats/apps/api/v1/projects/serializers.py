from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import (
    CustomStatus,
    CustomStatusType,
    FlowStart,
    LinkContact,
    Project,
    ProjectPermission,
)
from chats.apps.sectors.models import Sector


class ProjectSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)
    config = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "name",
            "date_format",
            "timezone",
            "config",
            "org",
            "room_routing_type",
        ]
        read_only_fields = [
            "timezone",
            "room_routing_type",
        ]

    def get_config(self, project: Project):
        from chats.core.cache_utils import get_project_config_cached
        config = get_project_config_cached(str(project.uuid)) or project.config
        if config is not None and "chat_gpt_token" in config.keys():
            config = config.copy()
            config.pop("chat_gpt_token", None)
        return config


class LinkContactSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = LinkContact
        fields = ["user_email", "contact", "project"]

    def get_user_email(self, linked_contact: LinkContact) -> str:
        try:
            return linked_contact.user.email
        except AttributeError:
            return ""


class ProjectFlowContactSerializer(serializers.Serializer):
    uuid = serializers.CharField(required=False)
    name = serializers.CharField()
    language = serializers.CharField(required=False, max_length=3)
    urns = serializers.ListField(child=serializers.CharField(), max_length=100)
    groups = serializers.ListField(
        required=False, child=serializers.CharField(), max_length=100
    )
    fields = serializers.JSONField(
        required=False,
    )


class ProjectFlowStartSerializer(serializers.Serializer):
    groups = serializers.ListField(
        required=False, child=serializers.CharField(), max_length=100
    )
    contacts = serializers.ListField(
        required=False, child=serializers.CharField(), max_length=100
    )
    flow = serializers.CharField()
    room = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
        trim_whitespace=True,
    )
    params = serializers.JSONField(required=False)
    contact_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class ListFlowStartSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = FlowStart
        fields = ["contact_data", "name", "user", "created_on", "room"]

    def get_user(self, flow_start: FlowStart) -> str:
        try:
            return flow_start.permission.user.full_name
        except AttributeError:
            return ""


class SectorDiscussionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["uuid", "name"]


class ListProjectUsersSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.CharField(source="user.email")
    photo_url = serializers.CharField(source="user.photo_url")

    class Meta:
        model = ProjectPermission
        fields = ["first_name", "last_name", "email", "photo_url"]


class CustomStatusTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomStatusType
        fields = ["uuid", "name", "project", "is_deleted"]
        read_only_fields = ["uuid", "is_deleted"]

    def validate_name(self, name):
        if name == "In-Service":
            raise serializers.ValidationError("Invalid status name")
        return name


class CustomStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomStatus
        fields = [
            "uuid",
            "user",
            "status_type",
            "is_active",
            "break_time",
            "created_on",
        ]
        read_only_fields = [
            "uuid",
        ]

    break_time = serializers.IntegerField(required=False)


class LastStatusQueryParamsSerializer(serializers.Serializer):
    project_uuid = serializers.UUIDField(required=True)


class ContactUUIDQuerySerializer(serializers.Serializer):
    contact = serializers.UUIDField(required=True, help_text="UUID of the contact")


class CursorQuerySerializer(serializers.Serializer):
    cursor = serializers.CharField(
        required=False,
        help_text="Cursor of pagination returned by the previous endpoint",
    )


class FlowUUIDQuerySerializer(serializers.Serializer):
    flow = serializers.UUIDField(required=True, help_text="UUID of the flow")


class ProjectContactWarningQuerySerializer(serializers.Serializer):
    project = serializers.UUIDField(required=True)
    contact = serializers.UUIDField(required=True)


class FlowStartListQuerySerializer(serializers.Serializer):
    created_on_after = serializers.DateField(
        required=False, help_text="Filter flow starts created after this date (YYYY-MM-DD)"
    )
    created_on_before = serializers.DateField(
        required=False, help_text="Filter flow starts created before this date (YYYY-MM-DD)"
    )


class ProjectQuerySerializer(serializers.Serializer):
    project = serializers.UUIDField(required=True)


class ProjectVerifyAccessQuerySerializer(serializers.Serializer):
    project = serializers.UUIDField(required=True)


class ProjectPermissionListQuerySerializer(serializers.Serializer):
    project = serializers.UUIDField(required=False)
    sector = serializers.UUIDField(required=False)
    role = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
