from rest_framework import serializers

from ..models import DiscussionUser


class DiscussionUserListSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="permission.user.first_name", read_only=True
    )
    last_name = serializers.CharField(
        source="permission.user.last_name", read_only=True
    )
    email = serializers.CharField(source="permission.user.email", read_only=True)

    class Meta:
        model = DiscussionUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
        ]
