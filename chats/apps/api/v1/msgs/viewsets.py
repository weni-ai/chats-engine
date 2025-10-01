from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from pydub.exceptions import CouldntDecodeError
from rest_framework import filters, mixins, pagination, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.pagination import CustomCursorPagination
from chats.apps.api.v1.msgs.filters import MessageFilter, MessageMediaFilter
from chats.apps.api.v1.msgs.permissions import MessageMediaPermission, MessagePermission
from chats.apps.api.v1.msgs.serializers import (
    MessageAndMediaSerializer,
    MessageMediaSerializer,
    MessageSerializer,
)
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.rooms.models import RoomNote


class MessageViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ChatMessage.objects.select_related(
        "room", "user", "contact", "internal_note", "internal_note__user"
    ).prefetch_related("medias")
    serializer_class = MessageSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    permission_classes = [IsAuthenticated, MessagePermission]
    lookup_field = "uuid"

    pagination_class = CustomCursorPagination
    ordering = ["-created_on"]

    def get_paginated_response(self, data):
        if self.request.query_params.get("reverse_results", False):
            data.reverse()
        qs = super().get_paginated_response(data)
        return qs

    def create(self, request, *args, **kwargs):
        request.data["user"] = request.user

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()
            serializer.instance.notify_room("create", True)
            
            message = serializer.instance
            print(f"DEBUG - User: {message.user}, first_user_assigned_at: {message.room.first_user_assigned_at}")
            
            if message.user and message.room.first_user_assigned_at:
                previous_agent_messages = message.room.messages.filter(
                    user__isnull=False,
                    created_on__lt=message.created_on
                ).exists()
                
                print(f"DEBUG - Previous messages: {previous_agent_messages}")
                
                if not previous_agent_messages:
                    print("DEBUG - Disparando task!")
                    from chats.apps.dashboard.tasks import calculate_first_response_time_task
                    calculate_first_response_time_task.delay(str(message.room.uuid))

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_room("update", True)

    @action(
        methods=["POST"],
        detail=False,
        url_name="create_media",
        parser_classes=[parsers.MultiPartParser],
        serializer_class=MessageAndMediaSerializer,
    )
    def create_media(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_parsers(self):
        """
        OpenAPI cannot render nested serializer for MultiPartParser,
        this removes the file field from the Request Body schema doc
        """
        if getattr(self, "swagger_fake_view", False):
            return []

        return super().get_parsers()


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

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except CouldntDecodeError:
            return Response(
                {
                    "detail": "Could not decode audio file, possibility of corrupted file",
                    "status": "error",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()
            instance = serializer.instance
            instance.message.notify_room("update")
            instance.callback()
