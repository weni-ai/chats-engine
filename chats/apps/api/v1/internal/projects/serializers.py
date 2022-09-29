from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.api.v1.internal.users.serializers import UserSerializer


class ProjectInternalSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)
    is_template = serializers.BooleanField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            "uuid",
            "name",
            "date_format",
            "timezone",
            "is_template",
        ]

        extra_kwargs = {field: {"required": False} for field in fields}

    def create(self, validated_data):
        try:
            is_template = validated_data.pop("is_template")
        except KeyError:
            is_template = False

        instance = super().create(validated_data)
        if is_template is True:
            sector = instance.sectors.create(
                name="Setor Padrão", rooms_limit=5, work_start="08:00", work_end="18:00"
            )
            sector.queues.create(name="Fila 1")

        return instance


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

class CheckAccessReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPermission
        fields = [
           "first_access"
        ]

