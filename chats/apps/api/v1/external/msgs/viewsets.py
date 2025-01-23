from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.msgs.filters import MessageFilter
from chats.apps.api.v1.external.msgs.serializers import MsgFlowSerializer
from chats.apps.api.v1.external.permissions import IsAdminPermission
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
            instances = []
            room = None
            for validated_data in serializer.validated_data:
                room = validated_data.get("room")
                if room.project_uuid != self.request.auth.project:
                    self.permission_denied(
                        self.request,
                        message="Ticketer token permission failed on room project",
                        code=403,
                    )
                validated_data["room"] = room
                instances.append(ChatMessage(**validated_data))
            created_instances = ChatMessage.objects.bulk_create(instances)

            if room:
                room.notify_room("create")

            if (
                room
                and room.user is None
                and any(instance.contact for instance in created_instances)
            ):
                room.trigger_default_message()

            return created_instances

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.notify_room("update")
