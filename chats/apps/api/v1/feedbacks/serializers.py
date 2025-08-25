from rest_framework import serializers


from chats.apps.projects.models import Project


class FeedbackSerializer(serializers.Serializer):
    """
    Serializer for feedback creation.
    """

    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(allow_blank=True, allow_null=True)
    project_uuid = serializers.UUIDField()

    def validate(self, attrs):
        """
        Validate the input data.
        """
        project_uuid = attrs.get("project_uuid")

        project = Project.objects.filter(uuid=project_uuid).first()

        if not project:
            raise serializers.ValidationError(
                {"project_uuid": ["Project not found"]}, code="not_found"
            )

        attrs["project"] = project

        return attrs
