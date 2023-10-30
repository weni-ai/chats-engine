from rest_framework import serializers

from ..models import Discussion
from ..services import create_discussion_message_and_notify


class RoomFlowSerializer(serializers.ModelSerializer):
    initial_message = serializers.CharField(
        required=True, write_only=True, allow_null=True
    )

    class Meta:
        model = Discussion
        fields = [
            "uuid",
            "room",
            "queue",
            "subject",
        ]
        read_only_fields = [
            "uuid",
        ]

    def create(self, validated_data):
        initial_message = validated_data.pop("initial_message")
        discussion = super().create(validated_data)
        discussion.notify("create")
        create_discussion_message_and_notify(discussion, initial_message)
        return discussion
