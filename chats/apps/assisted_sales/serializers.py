from rest_framework import serializers

from chats.apps.assisted_sales.models import CopilotIntegration
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


class UpdateCopilotIntegrationSerializer(serializers.Serializer):
    new_uuid = serializers.UUIDField()


class CreateCopilotIntegrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
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

    class Meta:
        model = CopilotIntegration
        fields = [
            "name",
            "assigned_agents",
            "created_on",
            "connected_on",
            "uuid",
            "connected_by",
        ]

    def get_created_on(self, obj: CopilotIntegration):
        return obj.copilot_created_on or obj.created_on

    def get_connected_by(self, obj: CopilotIntegration):
        if not obj.connected_by:
            return ""
        return obj.connected_by.name or obj.connected_by.email
