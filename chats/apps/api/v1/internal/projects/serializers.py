from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.api.v1.internal.users.serializers import UserSerializer


class ProjectInternalSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)

    class Meta:
        model = Project
        fields = [
            "uuid",
            "name",
            "date_format",
            "timezone",
        ]
        read_only_fields = [
            "uuid",
        ]

        extra_kwargs = {field: {"required": False} for field in fields}


class ProjectPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPermission
        fields = [
            "uuid",
            "created_on",
            "modified_on",
            "role",
            "project",
            "user",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class ProjectPermissionReadSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False)

    class Meta:
        model = ProjectPermission
        fields = [
            "uuid",
            "created_on",
            "modified_on",
            "role",
            "project",
            "user",
        ]
