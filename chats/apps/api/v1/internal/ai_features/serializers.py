from rest_framework import serializers

from chats.apps.ai_features.models import FeaturePrompt


class FeaturePromptWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturePrompt
        fields = ["uuid", "feature", "model", "settings", "prompt", "version"]


class FeaturePromptReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturePrompt
        fields = ["feature", "version"]
