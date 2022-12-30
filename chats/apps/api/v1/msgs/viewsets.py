from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, pagination, parsers, viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.msgs.filters import MessageFilter, MessageMediaFilter
from chats.apps.api.v1.msgs.serializers import (
    MessageMediaSerializer,
    MessageSerializer,
)
from chats.apps.api.v1.msgs.permissions import MessagePermission, MessageMediaPermission
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia


class MessageViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ChatMessage.objects.all()
    serializer_class = MessageSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    permission_classes = [IsAuthenticated, MessagePermission]
    # pagination_class = pagination.PageNumberPagination
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        # TODO USE THE REQUEST.USER TO SET THE USER IN THE MESSAGE
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):

        serializer.save()
        serializer.instance.notify_room("create", True)

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_room("update", True)


class MessageMediaViewset(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = MessageMedia.objects.all()
    serializer_class = MessageMediaSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageMediaFilter
    parser_classes = [parsers.MultiPartParser]
    permission_classes = [IsAuthenticated, MessageMediaPermission]
    pagination_class = pagination.PageNumberPagination
    lookup_field = "uuid"

    def get_queryset(self):
        if self.request.query_params.get("contact") or self.request.query_params.get(
            "project"
        ):
            return super().get_queryset()
        return self.queryset.none()

    def perform_create(self, serializer):
        serializer.save()
        instance = serializer.instance
        instance.message.notify_room("update")
        instance.callback()
