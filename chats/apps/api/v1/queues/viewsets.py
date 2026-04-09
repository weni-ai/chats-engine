import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from chats.apps.core.internal_domains import (
    is_vtex_internal_domain,
    exclude_vtex_internal_domains,
)
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.permissions import (
    IsQueueAgent,
    IsSectorManager,
    ProjectAnyPermission,
)
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueAuthorizationFilter, QueueFilter
from chats.apps.api.v1.rooms.services.bulk_close_service import BulkCloseService
from chats.apps.api.v1.rooms.services.bulk_transfer_service import BulkTransferService
from chats.apps.projects.models.models import Project
from chats.apps.projects.usecases.integrate_ticketers import IntegratedTicketers
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorGroupSector
from chats.apps.sectors.usecases.group_sector_authorization import (
    QueueGroupSectorAuthorizationCreationUseCase,
)
from chats.core.cache_utils import get_user_id_by_email_cached

from .serializers import (
    QueueAgentsSerializer,
    QueuePermissionsListQueryParamsSerializer,
)

LOGGER = logging.getLogger(__name__)

User = get_user_model()


@method_decorator(name="create", decorator=swagger_auto_schema(auto_schema=None))
@method_decorator(name="update", decorator=swagger_auto_schema(auto_schema=None))
@method_decorator(name="partial_update", decorator=swagger_auto_schema(auto_schema=None))
@method_decorator(name="destroy", decorator=swagger_auto_schema(auto_schema=None))
class QueueViewset(ModelViewSet):
    swagger_tag = "Queues"
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = QueueFilter
    permission_classes = []

    lookup_field = "uuid"

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["list", "transfer_agents"]:
            permission_classes = [IsAuthenticated, ProjectAnyPermission]
        elif self.action == "rooms_count":
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsSectorManager]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None

        qs = super().get_queryset()
        if self.request.query_params.get("is_deleted", None) is not None:
            qs = qs.filter(is_deleted=self.request.query_params.get("is_deleted", None))
        else:
            qs = qs.exclude(is_deleted=True)

        if self.action == "rooms_count":
            return qs

        # Allow all projects for internal communication users
        if self.request.user.has_perm("accounts.can_communicate_internally"):
            return qs

        # Allow only projects where the user has access
        return qs.filter(sector__project__permissions__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return queue_serializers.QueueReadOnlyListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        instance = serializer.save()

        project = Project.objects.get(uuid=instance.sector.project.uuid)

        use_group_sectors = SectorGroupSector.objects.filter(
            sector=instance.sector
        ).exists()
        if use_group_sectors:
            QueueGroupSectorAuthorizationCreationUseCase(instance).execute()

        if not settings.USE_WENI_FLOWS:
            return super().perform_create(serializer)

        should_use_integration = (
            project.config
            and project.config.get("its_principal", False)
            and instance.sector.secondary_project
        )

        if not should_use_integration:
            content = {
                "uuid": str(instance.uuid),
                "name": instance.name,
                "sector_uuid": str(instance.sector.uuid),
                "project_uuid": str(instance.sector.project.uuid),
            }
            response = FlowRESTClient().create_queue(**content)
            if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
                instance.delete()
                raise exceptions.APIException(
                    detail=f"[{response.status_code}] Error posting the queue on flows. Exception: {response.content}"
                )
        else:
            integrate_use_case = IntegratedTicketers()
            integrate_use_case.integrate_individual_topic(
                project, instance.sector.secondary_project
            )

        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        content = {
            "uuid": str(instance.uuid),
            "name": instance.name,
            "sector_uuid": str(instance.sector.uuid),
        }

        if not settings.USE_WENI_FLOWS:
            return super().perform_create(serializer)

        response = FlowRESTClient().update_queue(**content)

        if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            LOGGER.error(
                "[%s] Error updating the queue on Flows. Exception: %s",
                response.status_code,
                response.content,
            )

        return instance

    def _close_active_rooms(self, instance):
        rooms = Room.objects.filter(
            queue=instance,
            is_active=True,
        )
        if not rooms.exists():
            return None

        service = BulkCloseService()
        result = service.close(
            rooms=rooms,
            end_by="queue_deleted",
        )

        if result.success_count == 0 and result.failed_count > 0:
            raise exceptions.APIException(
                detail=(
                    f"Failed to close all {result.failed_count} active rooms "
                    f"for queue {instance.uuid}. Deletion aborted."
                ),
            )

        if result.failed_count > 0:
            LOGGER.warning(
                "[QUEUE_DELETE] Partial room closure for queue %s: "
                "%d succeeded, %d failed",
                instance.uuid,
                result.success_count,
                result.failed_count,
            )

        return result

    def _transfer_active_rooms(self, instance, target_queue):
        rooms = Room.objects.filter(
            queue=instance,
            is_active=True,
        )
        if not rooms.exists():
            return None

        service = BulkTransferService()
        return service.transfer(
            rooms=rooms,
            user_request=self.request.user,
            queue=target_queue,
        )

    def _validate_transfer_queue(self, instance, transfer_to_queue_uuid):
        try:
            target_queue = Queue.objects.select_related("sector__project").get(
                uuid=transfer_to_queue_uuid
            )
        except Queue.DoesNotExist:
            return None, Response(
                {"detail": f"Target queue {transfer_to_queue_uuid} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if target_queue.uuid == instance.uuid:
            return None, Response(
                {"detail": "Cannot transfer rooms to the same queue being deleted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_queue.sector.project_id != instance.sector.project_id:
            return None, Response(
                {"detail": "Target queue must belong to the same project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return target_queue, None

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        transfer_to_queue_uuid = request.query_params.get("transfer_to_queue")
        end_all_chats = (
            request.query_params.get("end_all_chats", "").lower() == "true"
        )

        if transfer_to_queue_uuid and end_all_chats:
            return Response(
                {"detail": "Cannot use both 'transfer_to_queue' and 'end_all_chats'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if transfer_to_queue_uuid:
            target_queue, error_response = self._validate_transfer_queue(
                instance, transfer_to_queue_uuid
            )
            if error_response:
                return error_response

            result = self._transfer_active_rooms(instance, target_queue)

            if result and result.failed_count > 0:
                return Response(
                    {
                        "detail": "Failed to transfer all rooms. Deletion aborted.",
                        "transfer": result.to_dict(),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            self.perform_destroy(instance)
            return Response(
                {
                    "is_deleted": True,
                    "transfer": result.to_dict() if result else None,
                },
                status=status.HTTP_200_OK,
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        end_all_chats = (
            self.request.query_params.get("end_all_chats", "").lower() == "true"
        )

        if end_all_chats:
            self._close_active_rooms(instance)

        secondary_project_config = instance.sector.secondary_project or {}
        secondary_project_uuid = secondary_project_config.get("uuid")

        project_uuid = secondary_project_uuid or instance.sector.project.uuid

        content = {
            "uuid": str(instance.uuid),
            "sector_uuid": str(instance.sector.uuid),
            "project_uuid": str(project_uuid),
        }

        if not settings.USE_WENI_FLOWS:
            return super().perform_destroy(instance)

        response = FlowRESTClient().destroy_queue(**content)

        if response.status_code == status.HTTP_404_NOT_FOUND:
            return super().perform_destroy(instance)

        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            raise exceptions.APIException(
                detail=f"[{response.status_code}] Error deleting the queue on flows. Exception: {response.content}"
            )
        return super().perform_destroy(instance)

    @action(detail=True, methods=["POST"])
    def authorization(self, request, *args, **kwargs):
        queue = self.get_object()
        user_email = request.data.get("user")
        if not user_email:
            return Response(
                {"Detail": "'user' field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permission = queue.get_permission(user_email)
        if not permission:
            return Response(
                {
                    "Detail": f"user {user_email} does not have an account or permission in this project"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queue_auth = queue.set_user_authorization(permission, 1)

        return Response(
            {
                "uuid": str(queue_auth.uuid),
                "user": queue_auth.permission.user.email,
                "queue": queue_auth.sector.name,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["GET"])
    def transfer_agents(self, *args, **kwargs):
        instance = self.get_object()
        agents = instance.agents

        queue_agents = agents.filter(
            project_permissions__queue_authorizations__role=1,
            project_permissions__queue_authorizations__queue=instance,
            project_permissions__is_deleted=False,
        )

        sector = Sector.objects.get(queues=instance)
        sector_agents = sector.managers

        project = Project.objects.get(sectors__queues=instance)
        project_admins = project.admins

        combined_permissions = queue_agents.union(sector_agents, project_admins)

        if isinstance(project.config, dict) and project.config.get(
            "filter_offline_agents", False
        ):
            online_queue_agents = instance.online_agents
            online_sector_managers = sector.online_managers
            online_admins = project.online_admins
            combined_permissions = online_queue_agents.union(
                online_sector_managers, online_admins
            )

        agents_pks = set(combined_permissions.values_list("id", flat=True))
        agents = User.objects.filter(id__in=agents_pks)

        user_email = self.request.user.email

        if not is_vtex_internal_domain(user_email):
            agents = exclude_vtex_internal_domains(agents)

        serializer = QueueAgentsSerializer(
            agents, many=True, context={"project": project}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"])
    def bulk_create(self, request, *args, **kwargs):
        serializer = queue_serializers.BulkQueueCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        sector = serializer.validated_data["sector"]
        queues_data = serializer.validated_data["queues"]

        project = Project.objects.get(uuid=sector.project.uuid)
        use_group_sectors = SectorGroupSector.objects.filter(sector=sector).exists()
        should_use_integration = (
            project.config
            and project.config.get("its_principal", False)
            and sector.secondary_project
        )

        created_queues = []

        with transaction.atomic():
            for queue_data in queues_data:
                queue_limit_data = queue_data.pop("queue_limit", None)
                queue = Queue.objects.create(
                    sector=sector,
                    name=queue_data["name"],
                    default_message=queue_data.get("default_message"),
                    config=queue_data.get("config"),
                    queue_limit=queue_limit_data.get("limit") if queue_limit_data else None,
                    is_queue_limit_active=queue_limit_data.get("is_active", False) if queue_limit_data else False,
                )

                if use_group_sectors:
                    QueueGroupSectorAuthorizationCreationUseCase(queue).execute()

                created_queues.append(queue)

        if not settings.USE_WENI_FLOWS:
            return Response(
                queue_serializers.QueueSerializer(
                    created_queues, many=True, context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED,
            )

        flows_registered = []
        try:
            for queue in created_queues:
                if should_use_integration:
                    IntegratedTicketers().integrate_individual_topic(
                        project, sector.secondary_project
                    )
                else:
                    content = {
                        "uuid": str(queue.uuid),
                        "name": queue.name,
                        "sector_uuid": str(sector.uuid),
                        "project_uuid": str(project.uuid),
                    }
                    response = FlowRESTClient().create_queue(**content)
                    if response.status_code not in [
                        status.HTTP_200_OK,
                        status.HTTP_201_CREATED,
                    ]:
                        raise exceptions.APIException(
                            detail=f"[{response.status_code}] Error posting the queue on flows. Exception: {response.content}"
                        )
                    flows_registered.append(queue)
        except exceptions.APIException:
            for registered_queue in flows_registered:
                FlowRESTClient().destroy_queue(
                    uuid=str(registered_queue.uuid),
                    sector_uuid=str(sector.uuid),
                    project_uuid=str(project.uuid),
                )
            Queue.objects.filter(pk__in=[q.pk for q in created_queues]).delete()
            raise

        response_serializer = queue_serializers.QueueSerializer(
            created_queues, many=True, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["GET"])
    def list_queue_permissions(self, request, *args, **kwargs):
        query_params = QueuePermissionsListQueryParamsSerializer(
            data=request.query_params
        )
        query_params.is_valid(raise_exception=True)

        user_email = query_params.validated_data["user_email"]
        project = query_params.validated_data.get("project")

        email_l = (user_email or "").lower()
        if get_user_id_by_email_cached(email_l) is None:
            return Response({"user_permissions": []}, status=status.HTTP_200_OK)

        query_params = {
            "permission__user_id": email_l,
            "queue__is_deleted": False,
        }

        if project:
            query_params["queue__sector__project"] = project

        queue_permissions = QueueAuthorization.objects.filter(**query_params)
        serializer_data = queue_serializers.QueueAuthorizationSerializer(
            queue_permissions, many=True
        )

        return Response(
            {"user_permissions": serializer_data.data}, status=status.HTTP_200_OK
        )


class QueueAuthorizationViewset(ModelViewSet):
    swagger_tag = "Queues"
    queryset = QueueAuthorization.objects.all()
    serializer_class = queue_serializers.QueueAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueAuthorizationFilter
    permission_classes = []
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action in ["list", "update_queue_permissions"]:
            permission_classes = [IsAuthenticated, IsQueueAgent]
        else:
            permission_classes = [IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueAuthorizationReadOnlyListSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["PATCH"])
    def update_queue_permissions(self, request, *args, **kwargs):
        queue_permission = self.get_object()

        role = request.data.get("role")

        queue_permission.role = role
        queue_permission.save()

        serializer_data = queue_serializers.QueueAuthorizationUpdateSerializer(
            queue_permission
        )
        return Response(
            {"user_permission": serializer_data.data}, status=status.HTTP_200_OK
        )
