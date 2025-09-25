from functools import cached_property
import logging

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
from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.ai_features.history_summary.tasks import (
    cancel_history_summary_generation,
    generate_history_summary,
)
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.rooms.serializers import (
    RoomFlowSerializer,
    RoomListSerializer,
    RoomMetricsSerializer,
)
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.utils import (
    create_room_assigned_from_queue_feedback,
    start_queue_priority_routing,
)
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.rooms.views import (
    close_room,
    create_room_feedback_message,
    get_editable_custom_fields_room,
    update_custom_fields,
    update_flows_custom_fields,
)

from .filters import RoomFilter, RoomMetricsFilter

logger = logging.getLogger(__name__)


def add_user_or_queue_to_room(instance: Room, request):
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

    instance.add_transfer_to_history(feedback)

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
        print("request.headers")
        print(self.request.headers)

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

        if (
            room.queue.sector.project.has_chats_summary
            and room.messages.filter(
                Q(user__isnull=False) | Q(contact__isnull=False)
            ).exists()
        ):
            if not (
                history_summary := HistorySummary.objects.filter(
                    room=room, status=HistorySummaryStatus.PENDING
                ).first()
            ):
                history_summary = HistorySummary.objects.create(room=room)

            generate_history_summary.delay(history_summary.uuid)

        return Response(status=status.HTTP_201_CREATED)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        print("Create room request data:")
        print(request.data)

        print("Create room request headers:")
        print(request.headers)

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

        instance.refresh_from_db()

        if instance.user:
            create_room_assigned_from_queue_feedback(instance, instance.user)

        room.notify_billing()

        if room.queue.sector.project.has_chats_summary:
            history_summary = HistorySummary.objects.create(room=room)

            if room.messages.filter(
                Q(user__isnull=False) | Q(contact__isnull=False)
            ).exists():
                generate_history_summary.delay(history_summary.uuid)

            else:
                cancel_history_summary_generation.apply_async(
                    args=[history_summary.uuid], countdown=30
                )  # 30 seconds delay

        if (
            instance.user
            and instance.queue.sector.is_automatic_message_active
            and instance.queue.sector.automatic_message_text
        ):
            instance.send_automatic_message(delay=1)

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
            agent = (filters.get("agent") or "").lower()
            project = room.project
            agent_permission = project.permissions.get(user_id=agent)
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
        room.save()
        room.add_transfer_to_history(feedback)

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
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]

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
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]

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
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]

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

    def list(self, request, *args, **kwargs):
        """
        Override para adicionar next e previous links
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)

            limit = int(
                request.query_params.get("limit", self.pagination_class.default_limit)
            )
            offset = int(request.query_params.get("offset", 0))
            total_count = queryset.count()

            base_url = request.build_absolute_uri().split("?")[0]
            query_params = request.query_params.copy()

            if (offset + limit) < total_count:
                query_params["offset"] = offset + limit
                query_params["limit"] = limit
                response.data["next"] = f"{base_url}?{query_params.urlencode()}"

            if offset > 0:
                query_params["offset"] = max(0, offset - limit)
                query_params["limit"] = limit
                response.data["previous"] = f"{base_url}?{query_params.urlencode()}"

            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]

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
