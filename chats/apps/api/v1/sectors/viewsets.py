from django.conf import settings
from django.db import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.internal.rest_clients.connect_rest_client import (
    ConnectRESTClient,
)
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.permissions import (
    HasAgentPermissionAnyQueueSector,
    IsProjectAdmin,
    IsSectorManager,
)
from chats.apps.api.v1.sectors import serializers as sector_serializers
from chats.apps.api.v1.sectors.filters import (
    SectorAuthorizationFilter,
    SectorFilter,
    SectorTagFilter,
)
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class SectorViewset(viewsets.ModelViewSet):
    queryset = Sector.objects.exclude(is_deleted=True)
    serializer_class = sector_serializers.SectorSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = SectorFilter
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action == "list":
            permission_classes = [IsAuthenticated]
        elif self.action in ["create", "destroy"]:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        elif self.action == "agents":
            permission_classes = [HasAgentPermissionAnyQueueSector]
        else:
            permission_classes = [IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "list":
            return sector_serializers.SectorReadOnlyListSerializer
        elif self.action == "retrieve":
            return sector_serializers.SectorReadOnlyRetrieveSerializer
        elif self.action == "update":
            return sector_serializers.SectorUpdateSerializer

        return super().get_serializer_class()

    def perform_create(self, serializer):
        try:
            instance = serializer.save()
        except IntegrityError as e:
            raise exceptions.APIException(
                detail=f"Error when saving the sector. Exception: {str(e)}"  # NOQA
            )
        content = {
            "project_uuid": str(instance.project.uuid),
            "name": instance.name,
            "config": {
                "project_auth": str(instance.external_token.pk),
                "sector_uuid": str(instance.uuid),
            },
        }

        if settings.USE_WENI_FLOWS:
            connect = ConnectRESTClient()
            response = connect.create_ticketer(**content)
            if response.status_code not in [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]:
                instance.delete()

                raise exceptions.APIException(
                    detail=f"[{response.status_code}] Error posting the sector/ticketer on flows. Exception: {response.content}"  # NOQA
                )

    def update(self, request, *args, **kwargs):
        sector = self.get_object()
        config = request.data.get("config")
        if config and config.get("can_use_chat_completion"):
            openai_token = sector.project.set_chat_gpt_auth_token(
                request.META.get("HTTP_AUTHORIZATION")
            )
            if not openai_token:
                return Response(
                    {
                        "detail": "There is no chatgpt token configured on the integrations module"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        content = {
            "sector_uuid": str(instance.uuid),
            "user_email": self.request.query_params.get("user_email"),
        }

        if not settings.USE_WENI_FLOWS:
            return super().perform_destroy(instance)

        response = FlowRESTClient().destroy_sector(**content)
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            raise exceptions.APIException(
                detail=f"[{response.status_code}] Error deleting the sector on flows. Exception: {response.content}"
            )
        instance.delete()
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )

    @action(detail=True, methods=["GET"])
    def agents(self, *args, **kwargs):
        instance = self.get_object()
        queue_agents = instance.queue_agents
        serializer = sector_serializers.SectorAgentsSerializer(queue_agents, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"])
    def count(self, request, *args, **kwargs):
        project_uuid = request.query_params.get("project")
        project = Project.objects.get(uuid=project_uuid)
        sector_count = project.get_sectors(user=request.user).count()
        # TODO: CREATE A METHOD DO COUNT SECTORS OF USER
        if sector_count == 0:
            sector_count = (
                Sector.objects.filter(
                    project=project,
                    queues__authorizations__permission__user=request.user,
                    is_deleted=False,
                )
                .distinct()
                .count()
            )
        return Response({"sector_count": sector_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def authorization(self, request, *args, **kwargs):
        sector = self.get_object()
        user_email = request.data.get("user")
        if not user_email:
            return Response(
                {"Detail": "'user' field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permission = sector.get_permission(user_email)
        if not permission:
            return Response(
                {
                    "Detail": f"user {user_email} does not have an account or permission in this project"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sector_auth = sector.set_user_authorization(permission, 1)

        return Response(
            {
                "uuid": str(sector_auth.uuid),
                "user": sector_auth.permission.user.email,
                "sector": sector_auth.sector.name,
            },
            status=status.HTTP_201_CREATED,
        )


class SectorTagsViewset(viewsets.ModelViewSet):
    queryset = SectorTag.objects.all()
    serializer_class = sector_serializers.SectorTagSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorTagFilter
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action == "list":
            permission_classes = [
                IsAuthenticated,
            ]
        else:
            permission_classes = (IsAuthenticated, IsSectorManager)

        return [permission() for permission in permission_classes]


class SectorAuthorizationViewset(viewsets.ModelViewSet):
    queryset = SectorAuthorization.objects.all()
    serializer_class = sector_serializers.SectorAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorAuthorizationFilter
    lookup_field = "uuid"

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["retrieve", "list"]:
            permission_classes = (IsAuthenticated, IsSectorManager)
        else:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return sector_serializers.SectorAuthorizationReadOnlySerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"detail": "The user already have authorization on this sector"},
                status.HTTP_400_BAD_REQUEST,
            )

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_user("destroy")
        super().perform_destroy(instance)
