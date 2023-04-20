from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.msgs.serializers import MsgFlowSerializer
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.msgs.filters import MessageFilter
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
    permission_classes = [IsAdminPermission]
    authentication_classes = [ProjectAdminAuthentication]
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.notify_room("create")
        room = instance.room
        if room.user is None:
            room.trigger_default_message()

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.notify_room("update")
