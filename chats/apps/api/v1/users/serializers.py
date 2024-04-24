from rest_framework import serializers

from chats.apps.accounts.models import Profile
from chats.apps.projects.models.models import ProjectPermission


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    project_permission_role = serializers.SerializerMethodField()

    def get_project_permission_role(self, obj):
        project_uuid = self.context.get("project_uuid")
        project_permission = ProjectPermission.objects.filter(
            project=project_uuid, user=obj.user
        ).first()

        if project_permission:
            return project_permission.role

    class Meta:
        model = Profile
        exclude = ["user", "uuid"]
