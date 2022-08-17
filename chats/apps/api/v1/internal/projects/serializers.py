from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.projects.models import Project, ProjectPermission


class ProjectInternalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class ProjectAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPermission
        fields = "__all__"
