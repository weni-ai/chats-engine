from rest_framework import serializers

from chats.apps.projects.models import ProjectPermission
from chats.apps.api.v1.internal.users.serializers import UserSerializer


class AgentFlowSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False)

    class Meta:
        model = ProjectPermission
        fields = [
            "user",
        ]
