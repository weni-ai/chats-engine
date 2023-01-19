import json

from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1.rooms.serializers import RoomSerializer, TransferRoomSerializer
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room
from chats.apps.api.v1.rooms import filters as room_filters
from chats.apps.api.v1 import permissions as api_permissions
from chats.utils.websockets import send_channels_group

from django.conf import settings 

from django.db.models import Count, Avg, F, Sum, DateTimeField


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

    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated]
        if self.action != "list":
            permission_classes = (
                permissions.IsAuthenticated,
                api_permissions.IsQueueAgent,
            )
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == "update":
            return TransferRoomSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["PUT", "PATCH"], url_name="close")
    def close(
        self, request, *args, **kwargs
    ):  # TODO: Remove the body options on swagger as it won't use any
        """
        Close a room, setting the ended_at date and turning the is_active flag as false
        """
        # Add send room notification to the channels group
        instance = self.get_object()
        tags = request.data.get("tags", None)
        instance.close(tags, "agent")
        serialized_data = RoomSerializer(instance=instance)
        instance.notify_queue("close", callback=True)

        if not settings.ACTIVATE_CALC_METRICS:
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        messages_contact = Message.objects.filter(room=instance, contact__isnull=False)
        messages_agent = Message.objects.filter(room=instance, user__isnull=False)

        time_message_contact = 0
        time_message_agent = 0

        if messages_contact and messages_agent:
            for i in messages_contact:
                time_message_contact += i.created_on.timestamp()

            for i in messages_agent:
                time_message_agent += i.created_on.timestamp()

            difference_time = time_message_contact - time_message_agent

            metric_room = RoomMetrics.objects.get(room=instance)
            metric_room.message_response_time = difference_time
            metric_room.save()

        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_queue("create")

    def perform_update(self, serializer):
        # TODO Separate this into smaller methods
        instance = self.get_object()
        transfer_history = instance.transfer_history or []

        old_queue = instance.queue

        user = self.request.data.get("user_email")
        queue = self.request.data.get("queue_uuid")
        serializer.save()

        if not (user or queue):
            return None

        instance = serializer.instance

        # Create transfer object based on whether it's a user or a queue transfer and add it to the history
        if user:
            if instance.user is None:
                time = timezone.now() - instance.modified_on
                room_metrics = RoomMetrics.objects.get_or_create(
                    room=instance, waiting_time=time.total_seconds()
                )
            else:
                _content = {"type": "user", "name": instance.user.first_name}
                transfer_history.append(_content)

            if instance.metric:
                instance.metric.queued_count += 1
                instance.metric.save()

        if queue:
            # Create constraint to make queue not none
            _content = {"type": "queue", "name": instance.queue.name}
            transfer_history.append(_content)
            if (
                not user
            ):  # if it is only a queue transfer from a user, need to reset the user field
                instance.user = None

        instance.transfer_history = transfer_history
        instance.save()

        # Create a message with the transfer data and Send to the room group
        msg = instance.messages.create(text=json.dumps(_content), seen=True)
        msg.notify_room("create")

        # Send Updated data to the room group
        instance.notify_room("update")

        # Force everyone on the queue group to exit the room Group
        send_channels_group(
            group_name=f"queue_{old_queue.pk}",
            call_type="exit",
            content={"name": "room", "id": str(instance.pk)},
            action="group.exit",
        )

        # Add the room group for the user or the queue that received it
        if user:
            send_channels_group(
                group_name=f"user_{instance.user.id}",
                call_type="join",
                content={"name": "room", "id": str(instance.pk)},
                action="group.join",
            )
            instance.notify_room("update")
            return None

        if queue:
            send_channels_group(
                group_name=f"queue_{instance.queue.pk}",
                call_type="join",
                content={"name": "room", "id": str(instance.pk)},
                action="group.join",
            )
            instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy", callback=True)
        super().perform_destroy(instance)
