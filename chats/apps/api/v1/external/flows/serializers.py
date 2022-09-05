from chats.apps.projects.models import Flow
from rest_framework import serializers


class FlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flow
        fields = [
            "uuid",
            "project_flows_uuid",
            "project",
        ]
        read_only_fields = [
            "uuid",
            "project",
        ]
