from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.ai_features.models import FeaturePrompt


class FeaturePromptWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturePrompt
        fields = ["uuid", "feature", "model", "settings", "prompt", "version"]

    def validate(self, attrs: dict) -> dict:
        feature = attrs.get("feature")
        version = attrs.get("version")

        if FeaturePrompt.objects.filter(feature=feature, version=version).exists():
            raise serializers.ValidationError(
                {"version": [_("Feature prompt with this version already exists")]},
                code="feature_prompt_version_already_exists",
            )

        return attrs


class FeaturePromptReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturePrompt
        fields = ["feature", "version"]
