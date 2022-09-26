from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework import status, exceptions
from django.conf import settings

from chats.apps.api.v1.permissions import IsSectorManager
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueFilter, QueueAuthorizationFilter
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.api.v1.internal.flows_rest_client import FlowRESTClient

if settings.USE_WENI_FLOWS:
    flow_client = FlowRESTClient()


class QueueViewset(ModelViewSet):
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFilter
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
        if self.action == "list":
            return queue_serializers.QueueReadOnlyListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        if not settings.USE_WENI_FLOWS:
            return super().perform_create(serializer)
        serializer.save()
        instance = serializer.instance
        response = flow_client.create_queue(
            str(instance.uuid), instance.name, str(instance.sector.uuid)
        )
        if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            instance.delete()
            raise exceptions.APIException(
                detail=f"Error posting the queue on flows. Exception: {response.content}"
            )
        return instance

    def perform_update(self, serializer):
        if not settings.USE_WENI_FLOWS:
            return super().perform_create(serializer)

        serializer.save()
        instance = serializer.instance
        response = flow_client.update_queue(
            str(instance.uuid), instance.name, str(instance.sector.uuid)
        )
        if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            raise exceptions.APIException(
                detail=f"Error updating the queue on flows. Exception: {response.content}"
            )
        return instance

    def perform_destroy(self, instance):
        if not settings.USE_WENI_FLOWS:
            return super().perform_destroy(instance)

        response = flow_client.destroy_queue(
            str(instance.uuid), str(instance.sector.uuid)
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            raise exceptions.APIException(
                detail=f"Error deleting the queue on flows. Exception: {response.content}"
            )
        return super().perform_destroy(instance)


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
