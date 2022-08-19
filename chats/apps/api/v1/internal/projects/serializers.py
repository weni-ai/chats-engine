from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import Project, ProjectPermission


class ProjectInternalSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)

    class Meta:
        model = Project
        fields = [
            "name",
            "date_format",
            "timezone",
        ]
        read_only_fields = [
            "timezone",
        ]


class ProjectPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPermission
        fields = "__all__"
