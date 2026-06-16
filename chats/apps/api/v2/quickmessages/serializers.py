from rest_framework import serializers

from chats.apps.quickmessages.models import QuickMessage


class SectorQuickMessageQueryParamsSerializer(serializers.Serializer):
    sector = serializers.UUIDField(required=False)
    project = serializers.UUIDField(required=False)

    def validate(self, attrs):
        sector = attrs.get("sector")
        project = attrs.get("project")

        if not sector and not project:
            raise serializers.ValidationError(
                "Provide either 'sector' or 'project' query parameter."
            )
        if sector and project:
            raise serializers.ValidationError(
                "Provide only one of 'sector' or 'project', not both."
            )
        return attrs


class SectorBriefSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()


class SectorQuickMessageResponseSerializer(serializers.ModelSerializer):
    sector = SectorBriefSerializer(read_only=True)

    class Meta:
        model = QuickMessage
        fields = ["uuid", "title", "shortcut", "text", "sector"]
        read_only_fields = fields
