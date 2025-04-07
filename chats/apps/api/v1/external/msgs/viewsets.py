from functools import cached_property
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.response import Response
from rest_framework import status

from chats.apps.accounts.authentication.drf.authorization import (
    get_auth_class,
)
from chats.apps.api.v1.external.msgs.filters import MessageFilter
from chats.apps.api.v1.external.msgs.serializers import MsgFlowSerializer
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.msgs.models import Message as ChatMessage


class MessageFlowViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ChatMessage.objects.all()
    serializer_class = MsgFlowSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    lookup_field = "uuid"

    @cached_property
    def authentication_classes(self):
        return get_auth_class(self.request)

    @cached_property
    def permission_classes(self):
        if self.request.auth:
            return [IsAdminPermission]
        return [ModuleHasPermission]

    def create(self, request, *args, **kwargs):
        is_batch = isinstance(request.data, list)
        if not is_batch:
            return super().create(request, *args, **kwargs)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        if isinstance(serializer.validated_data, list):
            # Verifica permissões para todos os rooms no batch
            for validated_data in serializer.validated_data:
                room = validated_data.get("room")
                if self.request.auth and room.project_uuid != self.request.auth.project:
                    self.permission_denied(
                        self.request,
                        message="Ticketer token permission failed on room project",
                        code=403,
                    )

            # Usa o método create do serializer que já suporta batch
            instances = serializer.save()

            # Processa notificações e trigger_default_message para cada mensagem
            rooms_processed = set()
            for instance in instances:
                room = instance.room
                if room and room.uuid not in rooms_processed:
                    room.notify_room("create")
                    rooms_processed.add(room.uuid)

                    if room.user is None and instance.contact:
                        room.trigger_default_message()

            return instances
        else:
            # Caso de mensagem única
            validated_data = serializer.validated_data
            room = validated_data.get("room")
            if self.request.auth and room.project_uuid != self.request.auth.project:
                self.permission_denied(
                    self.request,
                    message="Ticketer token permission failed on room project",
                    code=403,
                )
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            instance.notify_room("create")

            if instance.room.user is None and instance.contact:
                instance.room.trigger_default_message()

            return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.notify_room("update")
