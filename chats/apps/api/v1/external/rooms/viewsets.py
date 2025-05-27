import logging
from functools import cached_property

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination, LimitOffsetPagination
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
    get_auth_class,
)
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.rooms.serializers import (
    RoomFlowSerializer,
    RoomListSerializer,
    RoomMetricsSerializer,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.utils import (
    create_room_assigned_from_queue_feedback,
    start_queue_priority_routing,
)
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import (
    close_room,
    create_room_feedback_message,
    create_transfer_json,
    get_editable_custom_fields_room,
    update_custom_fields,
    update_flows_custom_fields,
)

from .filters import RoomFilter, RoomMetricsFilter

logger = logging.getLogger(__name__)


def add_user_or_queue_to_room(instance, request):
    # TODO Separate this into smaller methods
    user = request.data.get("user_email")
    queue = request.data.get("queue_uuid")

    # Create transfer object based on whether it's a user or a queue transfer and add it to the history
    if (user or queue) is None:
        return None

    if user and instance.user is not None:
        feedback = create_transfer_json(
            action="forward",
            from_="",
            to=instance.user,
        )
    if queue:
        feedback = create_transfer_json(
            action="forward",
            from_="",
            to=instance.queue,
        )
    instance.transfer_history = feedback
    instance.save()
    # Create a message with the transfer data and Send to the room group
    create_room_feedback_message(
        instance, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
    )

    return instance


class RoomFlowViewSet(viewsets.ModelViewSet):
    model = Room
    queryset = Room.objects.all()
    serializer_class = RoomFlowSerializer
    lookup_field = "uuid"

    @cached_property
    def authentication_classes(self):
        return get_auth_class(self.request)

    @cached_property
    def permission_classes(self):
        if self.request.auth and hasattr(self.request.auth, "project"):
            return [IsAdminPermission]
        return [ModuleHasPermission]

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
        if not settings.ACTIVATE_CALC_METRICS:
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        close_room(str(instance.pk))

        if instance.queue:
            logger.info(
                "Calling start_queue_priority_routing for room %s when closing it",
                instance.uuid,
            )
            start_queue_priority_routing(instance.queue)
        return Response(serialized_data.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def history(self, request, uuid=None):
        """
        Endpoint to create message history in an existing room.
        Reuses the existing process_message_history logic.
        """
        room = self.get_object()

        if (
            self.request.auth
            and hasattr(self.request.auth, "project")
            and room.project_uuid != self.request.auth.project
        ):
            return self.permission_denied(
                request,
                message="Ticketer token permission failed on room project",
                code=403,
            )

        messages_data = request.data
        if not isinstance(messages_data, list):
            messages_data = [messages_data]

        serializer = RoomFlowSerializer()
        serializer.process_message_history(room, messages_data)

        return Response(status=status.HTTP_201_CREATED)

    @transaction.atomic
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
        validated_data = serializer.validated_data
        queue_or_sector = validated_data.get("queue") or validated_data.get("sector")
        project = queue_or_sector.project

        if (
            self.request.auth
            and hasattr(self.request.auth, "project")
            and str(project.pk) != self.request.auth.project
        ):
            self.permission_denied(
                self.request,
                message="Ticketer token permission failed on room project",
                code=403,
            )
        room: Room = serializer.save()
        if room.flowstarts.exists():
            instance = room
            notification_type = "update"
        else:
            instance = add_user_or_queue_to_room(room, self.request)
            notification_type = "create"

        notify_level = "user" if instance.user else "queue"

        notification_method = getattr(instance, f"notify_{notify_level}")
        notification_method(notification_type)

        if instance.user:
            create_room_assigned_from_queue_feedback(instance, instance.user)

        room.notify_billing()

    def perform_update(self, serializer):
        serializer.save()
        instance = serializer.instance
        add_user_or_queue_to_room(instance, self.request)

        instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")

        super().perform_destroy(instance)


class RoomUserExternalViewSet(viewsets.ViewSet):
    serializer_class = RoomFlowSerializer
    permission_classes = [
        IsAdminPermission,
    ]
    authentication_classes = [ProjectAdminAuthentication]

    def partial_update(self, request, pk=None):
        if pk is None:
            return Response(
                {"Detail": "No ticket id on the request"}, status.HTTP_400_BAD_REQUEST
            )
        request_permission = self.request.auth
        project = request_permission.project
        room = (
            Room.objects.filter(
                (Q(ticket_uuid=pk) | Q(callback_url__endswith=pk))
                & Q(project_uuid=project)
                & Q(is_active=True)
            )
            .select_related("user", "queue__sector__project")
            .first()
        )
        if room is None:
            return Response(
                {
                    "Detail": "Ticket with the given id was not found, it does not exist or it is closed"
                },
                status.HTTP_404_NOT_FOUND,
            )

        if room.user:
            return Response(
                {
                    "Detail": "This ticket already has an agent, you can only add agents to queued rooms"
                },
                status.HTTP_400_BAD_REQUEST,
            )
        filters = self.request.data

        if not filters or not filters.get("agent"):
            return Response(
                {
                    "Detail": "Agent field can't be blank, the agent is needed to update the ticket"
                },
                status.HTTP_400_BAD_REQUEST,
            )
        try:
            agent = filters.get("agent")
            project = room.project
            agent_permission = project.permissions.get(user__email=agent)
        except ObjectDoesNotExist:
            return Response(
                {
                    "Detail": "Given agent not found on this project. Make sure it's an admin on the ticket's project"
                },
                status.HTTP_404_NOT_FOUND,
            )
        modified_on = room.modified_on
        room.user = agent_permission.user

        feedback = create_transfer_json(
            action="forward",
            from_="",
            to=room.user,
        )
        room.transfer_history = feedback
        room.save()

        room.notify_user("update", user=None)
        room.notify_queue("update")
        room.update_ticket()

        create_room_feedback_message(
            room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
        )

        time = timezone.now() - modified_on
        room_metric = RoomMetrics.objects.get_or_create(room=room)[0]
        room_metric.waiting_time += time.total_seconds()
        room_metric.queued_count += 1
        room_metric.save()

        return Response(
            {"Detail": f"Agent {agent} successfully attributed to the ticket {pk}"},
            status.HTTP_200_OK,
        )


class CustomFieldsUserExternalViewSet(viewsets.ViewSet):
    serializer_class = RoomFlowSerializer
    authentication_classes = [ProjectAdminAuthentication]

    def partial_update(self, request, pk=None):
        custom_fields_update = request.data
        data = {"fields": custom_fields_update}

        if pk is None:
            return Response(
                {"Detail": "No contact id on the request"}, status.HTTP_400_BAD_REQUEST
            )
        elif not custom_fields_update:
            return Response(
                {"Detail": "No custom fields the request"}, status.HTTP_400_BAD_REQUEST
            )
        request_permission = self.request.auth
        project = request_permission.project

        room = get_editable_custom_fields_room(
            {
                "contact__external_id": pk,
                "queue__sector__project": project,
                "is_active": "True",
            }
        )

        custom_field_name = list(data["fields"])[0]
        old_custom_field_value = room.custom_fields.get(custom_field_name, None)
        new_custom_field_value = data["fields"][custom_field_name]

        update_flows_custom_fields(
            project=room.project,
            data=data,
            contact_id=room.contact.external_id,
        )

        update_custom_fields(room, custom_fields_update)

        feedback = {
            "user": request_permission.user_first_name,
            "custom_field_name": custom_field_name,
            "old": old_custom_field_value,
            "new": new_custom_field_value,
        }

        create_room_feedback_message(
            room, feedback, method=RoomFeedbackMethods.EDIT_CUSTOM_FIELDS
        )

        return Response(
            {"Detail": "Custom Field edited with success"},
            status.HTTP_200_OK,
        )


class ExternalListRoomsViewSet(viewsets.ReadOnlyModelViewSet):
    model = Room
    queryset = Room.objects
    serializer_class = RoomListSerializer
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_on"]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomFilter

    pagination_class = CursorPagination
    pagination_class.page_size = 5

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(queue__sector__project=self.request.auth.project)
        )

    @action(detail=False, methods=["GET"], url_name="count")
    def count(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).filter(is_active=True)
        waiting = queryset.filter(user__isnull=True).count()
        in_service = queryset.filter(user__isnull=False).count()

        return Response(
            {"waiting": waiting, "in_service": in_service}, status=status.HTTP_200_OK
        )


class ExternalListWithPaginationRoomsViewSet(viewsets.ReadOnlyModelViewSet):
    model = Room
    queryset = Room.objects
    serializer_class = RoomListSerializer
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_on"]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomMetricsFilter

    pagination_class = LimitOffsetPagination
    pagination_class.default_limit = 10
    pagination_class.max_limit = 100

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(queue__sector__project=self.request.auth.project)
        )

    @action(detail=False, methods=["GET"], url_name="count")
    def count(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).filter(is_active=True)
        waiting = queryset.filter(user__isnull=True).count()
        in_service = queryset.filter(user__isnull=False).count()

        return Response(
            {"waiting": waiting, "in_service": in_service}, status=status.HTTP_200_OK
        )


class RoomMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    model = Room
    queryset = Room.objects.select_related("user").prefetch_related("messages", "tags")
    serializer_class = RoomMetricsSerializer
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_on"]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomMetricsFilter
    pagination_class = None

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(queue__sector__project=self.request.auth.project)
        )
