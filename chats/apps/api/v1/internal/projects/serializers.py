from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import exceptions, serializers, status
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.internal.users.serializers import UserSerializer
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization
from chats.apps.sectors.models import SectorAuthorization, SectorTag
from chats.core.cache_utils import get_user_id_by_email_cached

User = get_user_model()


class ProjectInternalSerializer(serializers.ModelSerializer):
    _ticketer_data = None
    _queue_data = None
    ticketer = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
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
            "ticketer",
            "queue",
            "is_csat_enabled",
        ]

        extra_kwargs = {field: {"required": False} for field in fields}

    def get_ticketer(self, *args, **kwargs):
        return self._ticketer_data or {}

    def get_queue(self, *args, **kwargs):
        return self._queue_data or {}

    def create(self, validated_data):
        try:
            is_template = validated_data.pop("is_template")
            user_email = validated_data.pop("user_email")
        except KeyError:
            is_template = False

        instance = super().create(validated_data)
        if is_template is True:
            email_l = (user_email or "").lower()
            if get_user_id_by_email_cached(email_l) is None:
                raise exceptions.APIException(detail="User not found")
            permission, created = instance.permissions.get_or_create(
                user_id=email_l, role=1
            )
            sector = instance.sectors.create(
                name="Default Sector",
                rooms_limit=5,
                work_start="08:00",
                work_end="18:00",
            )
            queue = sector.queues.create(name="Queue 1")
            SectorAuthorization.objects.create(
                role=1, permission=permission, sector=sector
            )
            QueueAuthorization.objects.create(
                role=1, permission=permission, queue=queue
            )
            SectorTag.objects.create(name="Atendimento encerrado", sector=sector)

            flows_client = FlowRESTClient()

            if settings.USE_WENI_FLOWS:
                response_sector = flows_client.create_ticketer(
                    project_uuid=str(instance.uuid),
                    name=sector.name,
                    config={
                        "project_auth": str(sector.external_token.pk),
                        "sector_uuid": str(sector.uuid),
                    },
                )

            self._ticketer_data = {
                "uuid": response_sector.json().get("uuid"),
                "name": sector.name,
            }
            self._queue_data = {"uuid": str(queue.pk), "name": queue.name}

            response_queue = flows_client.create_queue(
                uuid=str(queue.uuid),
                project_uuid=str(instance.uuid),
                name=queue.name,
                sector_uuid=str(queue.sector.uuid),
            )
            status_list = [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]

            if (response_sector.status_code not in status_list) or (
                response_queue.status_code not in status_list
            ):
                instance.delete()
                error_message = (
                    f"[{response_sector.status_code}] Sector response: {response_sector.content}. "
                    f"[{response_queue.status_code}] Queue response: {response_queue.content}."
                )
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
