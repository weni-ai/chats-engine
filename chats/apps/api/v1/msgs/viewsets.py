from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, pagination, parsers, viewsets, filters
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.msgs.filters import MessageFilter, MessageMediaFilter
from chats.apps.api.v1.msgs.serializers import MessageMediaSerializer, MessageSerializer
from chats.apps.api.v1.msgs.permissions import MessagePermission, MessageMediaPermission
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia


# class SectorPagination(pagination.)


class MessageViewset(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ChatMessage.objects
    serializer_class = MessageSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    permission_classes = [IsAuthenticated, MessagePermission]
    pagination_class = pagination.PageNumberPagination

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_room("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_room("update")


class MessageMediaViewset(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = MessageMedia.objects
    serializer_class = MessageMediaSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageMediaFilter
    parser_classes = [parsers.MultiPartParser]
    permission_classes = [IsAuthenticated, MessageMediaPermission]
    pagination_class = pagination.PageNumberPagination

    def get_queryset(self):
        if self.request.query_params.get("contact"):
            return super().get_queryset()
        return self.queryset.none()

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.message.notify_room("update")
