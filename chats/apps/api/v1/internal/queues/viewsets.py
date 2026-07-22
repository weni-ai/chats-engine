from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueFilter
from chats.apps.api.v1.internal.eda_clients.change_history_client import (
    publish_change_history,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.core.audit import apply_audit_fields


class QueueInternalViewset(viewsets.ModelViewSet):
    swagger_tag = "Queues"
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFilter
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueReadOnlyListSerializer
        if self.action == "update":
            return queue_serializers.QueueUpdateSerializer
        return super().get_serializer_class()

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return Response({"is_deleted": True}, status.HTTP_200_OK)

    def perform_create(self, serializer):
        instance = serializer.save(
            created_by=self.request.user, modified_by=self.request.user
        )
        publish_change_history(after=instance, user=self.request.user)

    def perform_update(self, serializer):
        before = Queue.objects.get(pk=serializer.instance.pk)
        instance = serializer.save(modified_by=self.request.user)
        publish_change_history(
            before=before,
            after=instance,
            user=self.request.user,
        )

    def perform_destroy(self, instance):
        apply_audit_fields(
            instance, self.request, instance.sector.project, on_delete=True
        )
        publish_change_history(before=instance, user=self.request.user)
        instance.is_deleted = True
        instance.save()


class QueueAuthInternalViewset(viewsets.ModelViewSet):
    swagger_tag = "Queues"
    queryset = QueueAuthorization.objects.all()
    serializer_class = queue_serializers.QueueAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["queue"]
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueAuthorizationReadOnlyListSerializer
        if self.action == "update":
            return queue_serializers.QueueAuthorizationUpdateSerializer
        return super().get_serializer_class()

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return Response({"is_deleted": True}, status.HTTP_200_OK)

    def perform_create(self, serializer):
        instance = serializer.save(
            created_by=self.request.user, modified_by=self.request.user
        )
        publish_change_history(after=instance, user=self.request.user)

    def perform_update(self, serializer):
        before = QueueAuthorization.objects.get(pk=serializer.instance.pk)
        instance = serializer.save(modified_by=self.request.user)
        publish_change_history(
            before=before,
            after=instance,
            user=self.request.user,
        )

    def perform_destroy(self, instance):
        apply_audit_fields(
            instance,
            self.request,
            instance.queue.sector.project,
            on_delete=True,
        )
        publish_change_history(before=instance, user=self.request.user)
        instance.is_deleted = True
        instance.save()
