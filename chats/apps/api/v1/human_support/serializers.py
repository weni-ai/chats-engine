from rest_framework import serializers


class HumanSupportNexusSettingsSerializer(serializers.Serializer):
    human_support = serializers.BooleanField(required=False)
    human_support_prompt = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one of 'human_support' or 'human_support_prompt' is required"
            )
        return attrs
