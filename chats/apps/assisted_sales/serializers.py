from rest_framework import serializers

from chats.apps.assisted_sales.models import CopilotIntegration
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector

COPILOT_NAME_MAX_LENGTH = 255


class UpdateCopilotIntegrationSerializer(serializers.Serializer):
    new_uuid = serializers.UUIDField(required=False)
    is_connected = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if attrs.get("is_connected") is True:
            return attrs
        if "new_uuid" not in attrs:
            raise serializers.ValidationError({"new_uuid": "This field is required."})
        return attrs


class CreateCopilotIntegrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=COPILOT_NAME_MAX_LENGTH)
    project = serializers.UUIDField()
    sector = serializers.UUIDField(required=False, allow_null=True)

    def validate_project(self, value):
        try:
            return Project.objects.get(uuid=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found")

    def validate_sector(self, value):
        if value is None:
            return None
        try:
            return Sector.objects.get(uuid=value)
        except Sector.DoesNotExist:
            raise serializers.ValidationError("Sector not found")


class CopilotIntegrationResponseSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    created_on = serializers.SerializerMethodField()
    connected_on = serializers.DateTimeField(read_only=True)
    connected_by = serializers.SerializerMethodField()
    is_connected = serializers.BooleanField(read_only=True)
    disconnected_by = serializers.SerializerMethodField()
    disconnected_on = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CopilotIntegration
        fields = [
            "name",
            "assigned_agents",
            "created_on",
            "connected_on",
            "uuid",
            "connected_by",
            "is_connected",
            "disconnected_by",
            "disconnected_on",
        ]

    def get_created_on(self, obj: CopilotIntegration):
        return obj.copilot_created_on or obj.created_on

    def get_connected_by(self, obj: CopilotIntegration):
        if not obj.connected_by:
            return ""
        return obj.connected_by.name or obj.connected_by.email

    def get_disconnected_by(self, obj: CopilotIntegration):
        if not obj.disconnected_by:
            return ""
        return obj.disconnected_by.name or obj.disconnected_by.email


class CopilotLinkedProjectSerializer(CopilotIntegrationResponseSerializer):
    project_uuid = serializers.UUIDField(source="copilot_project_uuid", read_only=True)
    connect_by = serializers.SerializerMethodField()

    class Meta(CopilotIntegrationResponseSerializer.Meta):
        fields = [
            "name",
            "assigned_agents",
            "created_on",
            "connected_on",
            "uuid",
            "project_uuid",
            "connect_by",
            "is_connected",
            "disconnected_by",
            "disconnected_on",
        ]

    def get_connect_by(self, obj: CopilotIntegration):
        return self.get_connected_by(obj)


class CopilotExistingProjectSerializer(serializers.Serializer):
    name = serializers.CharField()
    assigned_agents = serializers.IntegerField()
    uuid = serializers.UUIDField()
    project_uuid = serializers.UUIDField()


class CopilotConnectionSerializer(serializers.ModelSerializer):
    sector = serializers.UUIDField(source="sector_id", allow_null=True, read_only=True)
    project_uuid = serializers.UUIDField(source="copilot_project_uuid", read_only=True)
    conection = serializers.JSONField(source="connection", read_only=True)

    class Meta:
        model = CopilotIntegration
        fields = ["sector", "project_uuid", "conection"]
