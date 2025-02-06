from django.conf import settings
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.permissions import (
    IsQueueAgent,
    IsSectorManager,
    ProjectAnyPermission,
)
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueAuthorizationFilter, QueueFilter
from chats.apps.projects.models.models import Project
from chats.apps.projects.usecases.integrate_ticketers import IntegratedTicketers
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector

from .serializers import QueueAgentsSerializer

User = get_user_model()


class QueueViewset(ModelViewSet):
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
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return queue_serializers.QueueReadOnlyListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        instance = serializer.save()

        project = Project.objects.get(uuid=instance.sector.project.uuid)

        content = {
            "uuid": str(instance.uuid),
            "name": instance.name,
            "sector_uuid": str(instance.sector.uuid),
            "project_uuid": str(instance.sector.project.uuid),
        }
        if not settings.USE_WENI_FLOWS:
            return super().perform_create(serializer)
        response = FlowRESTClient().create_queue(**content)
        if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            instance.delete()
            raise exceptions.APIException(
                detail=f"[{response.status_code}] Error posting the queue on flows. Exception: {response.content}"
            )

        if project.config.get("its_principal"):
            integrate_use_case = IntegratedTicketers()
            integrate_use_case.integrate__individual_topic(
                project, instance.sector.config.get("integration_token")
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
            raise exceptions.APIException(
                detail=f"[{response.status_code}] Error updating the queue on flows. Exception: {response.content}"
            )
        return instance

    def perform_destroy(self, instance):
        content = {
            "uuid": str(instance.uuid),
            "sector_uuid": str(instance.sector.uuid),
            "project_uuid": str(instance.sector.project.uuid),
        }

        if not settings.USE_WENI_FLOWS:
            return super().perform_destroy(instance)

        response = FlowRESTClient().destroy_queue(**content)
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

        serializer = QueueAgentsSerializer(
            combined_permissions, many=True, context={"project": project}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"])
    def list_queue_permissions(self, request, *args, **kwargs):
        user_email = request.query_params.get("user_email")

        user = User.objects.get(email=user_email)
        project = request.query_params.get("project")

        queue_permissions = QueueAuthorization.objects.filter(
            permission__user=user,
            queue__sector__project=project,
            queue__is_deleted=False,
        )
        serializer_data = queue_serializers.QueueAuthorizationSerializer(
            queue_permissions, many=True
        )

        return Response(
            {"user_permissions": serializer_data.data}, status=status.HTTP_200_OK
        )


class QueueAuthorizationViewset(ModelViewSet):
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
