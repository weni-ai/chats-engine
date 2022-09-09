import json

from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError

from chats.apps.api.v1.rooms.serializers import RoomSerializer, TransferRoomSerializer
from chats.apps.rooms.models import Room
from chats.apps.api.v1.rooms import filters as room_filters
from chats.apps.api.v1 import permissions as api_permissions


class RoomViewset(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = room_filters.RoomFilter
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_permissions(self):
        permission_classes = self.permission_classes

        if self.action != "list":
            permission_classes.append(api_permissions.IsQueueAgent)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "update":
            return TransferRoomSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["PUT"], url_name="close")
    def close(
        self, request, *args, **kwargs
    ):  # TODO: Remove the body options on swagger as it won't use any
        """
        Close a room, setting the ended_at date and turning the is_active flag as false
        """
        # Add send room notification to the channels group
        instance = self.get_object()
        tags = request.data.get("tags", None)
        if tags is None:
            raise ValidationError(
                _("You cannot close a room without giving tags to it")
            )
        instance.close(tags, "agent")
        serialized_data = RoomSerializer(instance=instance)
        instance.notify_queue("close")
        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_queue("create")

    def perform_update(self, serializer):
        # TODO Separate this into smaller methods
        transfer_history = self.get_object().transfer_history
        transfer_history = (
            [] if transfer_history is None else json.loads(transfer_history)
        )
        user = self.request.data.get("user_email")
        queue = self.request.data.get("queue_uuid")
        serializer.save()
        instance = serializer.instance

        # Create transfer object based on whether it's a user or a queue transfer and add it to the history
        if user:
            _content = {"type": "user", "name": instance.user.first_name}
            transfer_history.append(_content)
        if queue:
            _content = {"type": "queue", "name": instance.queue.name}
            transfer_history.append(_content)

        instance.transfer_history = transfer_history
        instance.save()

        # Create a message with the transfer data and Send to the room group
        msg = instance.messages.create(text=json.dumps(_content))
        msg.notify_room("create")

        # Send Updated data to the room group
        instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")
        super().perform_destroy(instance)
