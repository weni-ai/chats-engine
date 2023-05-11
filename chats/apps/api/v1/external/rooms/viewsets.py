import json

from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.rooms.serializers import RoomFlowSerializer
from chats.apps.rooms.models import Room


def add_user_or_queue_to_room(instance, request):
    # TODO Separate this into smaller methods
    new_transfer_history = instance.transfer_history or []
    user = request.data.get("user_email")
    queue = request.data.get("queue_uuid")

    # Create transfer object based on whether it's a user or a queue transfer and add it to the history
    if (user or queue) is None:
        return None

    if user and instance.user is not None:
        _content = {"type": "user", "name": instance.user.first_name}
        new_transfer_history.append(_content)
    if queue:
        _content = {"type": "queue", "name": instance.queue.name}
        new_transfer_history.append(_content)
    instance.transfer_history = new_transfer_history
    instance.save()
    # Create a message with the transfer data and Send to the room group
    msg = instance.messages.create(text=json.dumps(_content), seen=True)
    msg.notify_room("create")

    return instance


class RoomFlowViewSet(viewsets.ModelViewSet):
    model = Room
    queryset = Room.objects.all()
    serializer_class = RoomFlowSerializer
    permission_classes = [
        IsAdminPermission,
    ]
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    @action(detail=True, methods=["PUT", "PATCH"], url_name="close")
    def close(
        self, request, *args, **kwargs
    ):  # TODO: Remove the body options on swagger as it won't use any
        """
        Close a room, setting the ended_at date and turning the is_active flag as false
        """
        instance = self.get_object()
        instance.close(None, "agent")
        serialized_data = RoomFlowSerializer(instance=instance)
        instance.notify_queue("close")
        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)

        except IntegrityError:
            return Response(
                {
                    "detail": "The contact already have an open room in the especified queue",
                },
                status.HTTP_400_BAD_REQUEST,
            )

    def perform_create(self, serializer):
        serializer.save()
        if serializer.instance.flowstarts.exists():
            instance = serializer.instance
            notification_type = "update"
        else:
            instance = add_user_or_queue_to_room(serializer.instance, self.request)
            notification_type = "create"

        notify_level = "user" if instance.user else "queue"
        # TODO REMOVE THIS. DEPRECATED (WONT USE ROOM GROUPS ANYMORE)
        # getattr(instance, f"{notify_level}_connection")(action="join")

        notification_method = getattr(instance, f"notify_{notify_level}")
        notification_method(notification_type)

    def perform_update(self, serializer):
        serializer.save()
        instance = serializer.instance
        add_user_or_queue_to_room(instance, self.request)

        instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")

        super().perform_destroy(instance)
