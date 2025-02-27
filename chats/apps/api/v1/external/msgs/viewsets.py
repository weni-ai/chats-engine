from functools import cached_property
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets

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

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        room = validated_data.get("room")
        if self.request.auth and room.project_uuid != self.request.auth.project:
            self.permission_denied(
                self.request,
                message="Ticketer token permission failed on room project",
                code=403,
            )
        instance = serializer.save()
        instance.notify_room("create")
        room = instance.room
        if room.user is None and instance.contact:
            room.trigger_default_message()

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.notify_room("update")
