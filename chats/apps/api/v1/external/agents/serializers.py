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
