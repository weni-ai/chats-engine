import json
from datetime import timedelta

from django.conf import settings
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    F,
    Max,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Concat
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1 import permissions as api_permissions
from chats.apps.api.v1.rooms import filters as room_filters
from chats.apps.api.v1.rooms.serializers import (
    RoomMessageStatusSerializer,
    RoomSerializer,
    TransferRoomSerializer,
)
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room


class RoomViewset(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    filter_backends = [
        OrderingFilter,
        DjangoFilterBackend,
        filters.SearchFilter,
    ]
    filterset_class = room_filters.RoomFilter
    search_fields = ["contact__name", "urn"]
    ordering_fields = "__all__"
    ordering = ["user", "-last_interaction"]
    pagination_class = CursorPagination
    pagination_class.page_size_query_param = "limit"

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
        qs = super().get_queryset()

        last_24h = timezone.now() - timedelta(days=1)

        qs = qs.annotate(
            last_interaction=Max("messages__created_on"),
            unread_msgs=Count("messages", filter=Q(messages__seen=False)),
            linked_user=Concat(
                "contact__linked_users__user__first_name",
                Value(" "),
                "contact__linked_users__user__last_name",
                filter=Q(contact__linked_users__project=F("queue__sector__project")),
                output_field=CharField(),
            ),
            last_contact_interaction=Max(
                "messages__created_on", filter=Q(messages__contact__isnull=False)
            ),
            is_24h_valid=Case(
                When(
                    Q(
                        urn__startswith="whatsapp",
                        last_contact_interaction__lt=last_24h,
                    ),
                    then=False,
                ),
                default=True,
                output_field=BooleanField(),
            ),
        )

        return qs

    def get_serializer_class(self):
        if "update" in self.action:
            return TransferRoomSerializer
        return super().get_serializer_class()

    @action(
        detail=True,
        methods=[
            "PATCH",
        ],
        url_name="bulk_update_msgs",
        serializer_class=RoomMessageStatusSerializer,
    )
    def bulk_update_msgs(self, request, *args, **kwargs):
        room = self.get_object()
        if room.user is None:
            return Response(
                {"detail": "Can't mark queued rooms as read"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RoomMessageStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serialized_data = serializer.validated_data

        message_filter = {"seen": not serialized_data.get("seen")}
        if request.data.get("messages", []):
            message_filter["pk__in"] = request.data.get("messages")

        room.messages.filter(**message_filter).update(
            modified_on=timezone.now(), seen=serialized_data.get("seen")
        )
        room.notify_user("update")
        return Response(
            {"detail": "All the given messages have been marked as read"},
            status=status.HTTP_200_OK,
        )

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
        instance.notify_user("close")

        if not settings.ACTIVATE_CALC_METRICS:
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        messages_contact = (
            Message.objects.filter(room=instance, contact__isnull=False)
            .order_by("created_on")
            .first()
        )
        messages_agent = (
            Message.objects.filter(room=instance, user__isnull=False)
            .order_by("created_on")
            .first()
        )

        time_message_contact = 0
        time_message_agent = 0

        if messages_agent and messages_contact:
            time_message_agent = messages_agent.created_on.timestamp()
            time_message_contact = messages_contact.created_on.timestamp()
        else:
            time_message_agent = 0
            time_message_contact = 0

        difference_time = time_message_agent - time_message_contact

        interation_time = (
            Room.objects.filter(pk=instance.pk)
            .aggregate(
                avg_time=Sum(
                    F("ended_at") - F("created_on"),
                )
            )["avg_time"]
            .total_seconds()
        )

        metric_room = RoomMetrics.objects.get_or_create(room=instance)[0]
        metric_room.message_response_time = difference_time
        metric_room.interaction_time = interation_time
        metric_room.save()

        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_queue("create")

    def perform_update(self, serializer):
        # TODO Separate this into smaller methods
        old_instance = self.get_object()
        transfer_history = old_instance.transfer_history or []
        old_user = old_instance.user

        user = self.request.data.get("user_email")
        queue = self.request.data.get("queue_uuid")
        serializer.save()

        if not (user or queue):
            return None

        instance = serializer.instance

        # Create transfer object based on whether it's a user or a queue transfer and add it to the history
        if user:
            if old_instance.user is None:
                time = timezone.now() - old_instance.modified_on
                room_metric = RoomMetrics.objects.get_or_create(room=instance)[0]
                room_metric.waiting_time += time.total_seconds()
                room_metric.queued_count += 1
                room_metric.save()
            else:
                # Get the room metric from instance and update the transfer_count value.
                room_metric = RoomMetrics.objects.get_or_create(room=instance)[0]
                room_metric.transfer_count += 1
                room_metric.save()

            transfer_content = {"type": "user", "name": instance.user.full_name}
            transfer_history.append(transfer_content)

        if queue:
            # Create constraint to make queue not none
            transfer_content = {"type": "queue", "name": instance.queue.name}
            transfer_history.append(transfer_content)
            if (
                not user
            ):  # if it is only a queue transfer from a user, need to reset the user field
                instance.user = None

            room_metric = RoomMetrics.objects.get_or_create(room=instance)[0]
            room_metric.transfer_count += 1
            room_metric.save()

        instance.transfer_history = transfer_history
        instance.save()

        # Create a message with the transfer data and Send to the room group
        msg = instance.messages.create(text=json.dumps(transfer_content), seen=True)
        msg.notify_room("create")

        if old_user is None and user:  # queued > agent
            instance.notify_queue("update")
        elif old_user is not None:
            instance.notify_user("update", user=old_user)
            if queue:  # agent > queue
                instance.notify_queue("update")
            else:  # agent > agent
                instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy", callback=True)
        super().perform_destroy(instance)
