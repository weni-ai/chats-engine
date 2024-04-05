from django.contrib.auth import get_user_model

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.permissions import AnyQueueAgentPermission, IsSectorManager
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueAuthorizationFilter, QueueFilter
from chats.apps.queues.models import Queue, QueueAuthorization

User = get_user_model()


class QueueViewset(ModelViewSet):
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = QueueFilter
    permission_classes = [
        IsAuthenticated,
        IsSectorManager,
    ]

    lookup_field = "uuid"

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action == "list":
            permission_classes = [
                IsAuthenticated,
                AnyQueueAgentPermission,
            ]

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
        content = {
            "uuid": str(instance.uuid),
            "name": instance.name,
            "sector_uuid": str(instance.sector.uuid),
        }
        if not settings.USE_WENI_FLOWS:
            return super().perform_create(serializer)
        response = FlowRESTClient().create_queue(**content)
        if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            instance.delete()
            raise exceptions.APIException(
                detail=f"[{response.status_code}] Error posting the queue on flows. Exception: {response.content}"
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

    @action(detail=False, methods=["GET"])
    def list_queue_permissions(self, request, *args, **kwargs):
        user_email = request.data.get("user_email")

        user = User.objects.get(email=user_email)
        project = request.data.get("project")

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
    permission_classes = [
        IsAuthenticated,
        IsSectorManager,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueAuthorizationReadOnlyListSerializer
        return super().get_serializer_class()
