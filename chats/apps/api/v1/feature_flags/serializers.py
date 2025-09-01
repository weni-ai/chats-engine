from rest_framework import serializers

from chats.apps.projects.models.models import Project


class FeatureFlagsQueryParamsSerializer(serializers.Serializer):
    """
    Serializer for the query params of the feature flags view.
    """

    project_uuid = serializers.UUIDField(required=True)

    def validate(self, attrs):
        project_uuid = attrs.get("project_uuid")

        attrs["project"] = Project.objects.filter(uuid=project_uuid).first()

        return attrs
