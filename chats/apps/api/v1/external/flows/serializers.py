from chats.apps.projects.models import Flow
from rest_framework import serializers


class FlowSerializer(serializers.ModelSerializer):
    model = Flow
    fields = "__all__"
    read_only_fields = [
        "uuid",
        "project",
    ]
