from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, exceptions, status
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.api.v1.internal.users.serializers import UserSerializer

from chats.apps.api.v1.internal.rest_clients.connect_rest_client import (
    ConnectRESTClient,
)
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from django.contrib.auth import get_user_model
from chats.apps.queues.models import QueueAuthorization
from chats.apps.sectors.models import SectorAuthorization, SectorTag

User = get_user_model()


class ProjectInternalSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)
    is_template = serializers.BooleanField(
        write_only=True, required=False, allow_null=True
    )
    user_email = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Project
        fields = [
            "uuid",
            "name",
            "date_format",
            "timezone",
            "is_template",
            "user_email",
        ]

        extra_kwargs = {field: {"required": False} for field in fields}

    def create(self, validated_data):
        try:
            is_template = validated_data.pop("is_template")
            user_email = validated_data.pop("user_email")
        except KeyError:
            is_template = False

        instance = super().create(validated_data)
        if is_template is True:
            user = User.objects.get(email=user_email)
            permission, created = instance.permissions.get_or_create(user=user, role=1)

            sector = instance.sectors.create(
                name="Setor Padrão", rooms_limit=5, work_start="08:00", work_end="18:00"
            )
            queue = sector.queues.create(name="Fila 1")
            sector_permission = SectorAuthorization.objects.create(
                role=1, permission=permission, sector=sector
            )
            queue_permission = QueueAuthorization.objects.create(
                role=1, permission=permission, queue=queue
            )
            tag = SectorTag.objects.create(name="Atendimento encerado", sector=sector)
            connect_client = ConnectRESTClient()
            response_sector = connect_client.create_ticketer(
                project_uuid=str(instance.uuid),
                name=sector.name,
                config={
                    "project_auth": str(permission.pk),
                    "sector_uuid": str(sector.uuid),
                },
            )

            flow_client = FlowRESTClient()
            response_flows = flow_client.create_queue(
                str(queue.uuid), queue.name, str(queue.sector.uuid)
            )
            status_list = [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]

            if (response_sector.status_code not in status_list) or (
                response_flows.status_code not in status_list
            ):
                instance.delete()
                error_message = f"[{response_sector.status_code}] Sector response: {response_sector.content}.  [{response_flows.status_code}] Queue response: {response_flows.content}."
                raise exceptions.APIException(detail=error_message)

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
        fields = ["first_access"]
