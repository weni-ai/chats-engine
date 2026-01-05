from functools import cached_property

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets

from chats.apps.accounts.authentication.drf.authorization import get_auth_class
from chats.apps.api.v1.external.msgs.filters import MessageFilter
from chats.apps.api.v1.external.msgs.serializers import MsgFlowSerializer
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.msgs.models import Message as ChatMessage


class MessageFlowViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    swagger_tag = "Integrations"
    queryset = ChatMessage.objects.all()
    serializer_class = MsgFlowSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    lookup_field = "uuid"
    throttle_classes = [
        ExternalSecondRateThrottle,  # Máx 20/seg
        ExternalMinuteRateThrottle,  # Máx 600/min
        ExternalHourRateThrottle,  # Máx 30k/hora
    ]

    @cached_property
    def authentication_classes(self):
        return get_auth_class(self.request)

    @cached_property
    def permission_classes(self):
        if self.request.auth and hasattr(self.request.auth, "project"):
            return [IsAdminPermission]
        return [ModuleHasPermission]

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        room = validated_data.get("room")
        if (
            self.request.auth
            and hasattr(self.request.auth, "project")
            and room.project_uuid != self.request.auth.project
        ):
            self.permission_denied(
                self.request,
                message="Ticketer token permission failed on room project",
                code=403,
            )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.notify_room("create")
        room = instance.room
        room.on_new_message(
            message=instance,
            contact=instance.contact,
            increment_unread=1,
        )
        if room.user is None and instance.contact:
            room.trigger_default_message()

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.notify_room("update")
