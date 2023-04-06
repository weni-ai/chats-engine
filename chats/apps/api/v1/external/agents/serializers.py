from rest_framework import serializers

from chats.apps.api.v1.internal.users.serializers import UserSerializer
from chats.apps.projects.models import ProjectPermission


class AgentFlowSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False)

    class Meta:
        model = ProjectPermission
        fields = [
            "user",
        ]
