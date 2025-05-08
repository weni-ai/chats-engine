from rest_framework import serializers

from chats.apps.ai_features.models import FeaturePrompt


class FeaturePromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturePrompt
        fields = ["uuid", "feature", "model", "settings", "prompt", "version"]
