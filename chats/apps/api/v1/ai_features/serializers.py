from rest_framework import serializers

from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageTypeChoices,
)


class AITextImprovementRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    type = serializers.ChoiceField(choices=ImprovedUserMessageTypeChoices.choices)
    project_uuid = serializers.UUIDField()
