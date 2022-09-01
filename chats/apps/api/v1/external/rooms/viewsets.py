import json

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.rooms.models import Room
from chats.apps.api.v1.external.rooms.serializers import RoomFlowSerializer
from chats.apps.api.v1.external.permissions import IsFlowPermission


class RoomFlowViewSet(viewsets.ModelViewSet):
    model = Room
    serializer_class = RoomFlowSerializer
    permission_classes = [
        IsFlowPermission,
    ]
    lookup_field = "uuid"

    @action(detail=True, methods=["PUT", "PATCH"], url_name="close")
    def close(
        self, request, *args, **kwargs
    ):  # TODO: Remove the body options on swagger as it won't use any
        """
        Close a room, setting the ended_at date and turning the is_active flag as false
        """
        # Add send room notification to the channels group
        instance = self.get_object()
        instance.close(None, "agent")
        serialized_data = RoomFlowSerializer(instance=instance)
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
