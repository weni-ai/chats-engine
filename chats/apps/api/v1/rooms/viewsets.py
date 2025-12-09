import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import (
    BooleanField,
    Case,
    Count,
    DateTimeField,
    Exists,
    Max,
    OuterRef,
    Q,
    Subquery,
    When,
)
from django.utils import timezone
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from chats.apps.api.v1.rooms.permissions import CanAddOrRemoveRoomTagPermission
from chats.core.cache_utils import get_user_id_by_email_cached
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.accounts.models import User
from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.api.utils import verify_user_room
from chats.apps.api.v1 import permissions as api_permissions
from chats.apps.api.v1.rooms.permissions import RoomNotePermission
from chats.apps.api.v1.internal.rest_clients.openai_rest_client import OpenAIClient
from chats.apps.api.v1.msgs.serializers import ChatCompletionSerializer
from chats.apps.api.v1.rooms import filters as room_filters
from chats.apps.api.v1.rooms.pagination import RoomListPagination
from chats.apps.api.v1.rooms.permissions import RoomNotePermission
from chats.apps.api.v1.rooms.serializers import (
    AddRoomTagSerializer,
    ListRoomSerializer,
    RemoveRoomTagSerializer,
    PinRoomSerializer,
    RoomHistorySummaryFeedbackSerializer,
    RoomHistorySummarySerializer,
    RoomInfoSerializer,
    RoomMessageStatusSerializer,
    RoomNoteSerializer,
    RoomSerializer,
    RoomTagSerializer,
    RoomsReportSerializer,
    TransferRoomSerializer,
)
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import start_queue_priority_routing
from chats.apps.sectors.models import SectorTag
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.exceptions import (
    MaxPinRoomLimitReachedError,
    RoomIsNotActiveError,
)
from chats.apps.rooms.models import Room, RoomNote, RoomPin
from chats.apps.rooms.services import RoomsReportService
from chats.apps.rooms.tasks import generate_rooms_report
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.rooms.views import (
    close_room,
    create_room_feedback_message,
    get_editable_custom_fields_room,
    update_custom_fields,
    update_flows_custom_fields,
)
from chats.apps.feature_flags.utils import is_feature_active

logger = logging.getLogger(__name__)


class RoomViewset(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        OrderingFilter,
    ]
    filterset_class = room_filters.RoomFilter
    search_fields = ["contact__name", "urn", "protocol", "service_chat"]
    ordering_fields = "__all__"
    ordering = ["user", "-last_interaction", "created_on", "added_to_queue_at"]

    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated]

        if self.action == "tags":
            permission_classes.append(api_permissions.HasObjectProjectPermission)

        elif self.action != "list":
            permission_classes = (
                permissions.IsAuthenticated,
                api_permissions.IsQueueAgent,
            )
        return [permission() for permission in permission_classes]

    @property
    def pagination_class(self):
        if self.action == "list":
            return RoomListPagination

        return super().pagination_class

    def get_queryset(
        self,
    ):  # TODO: sparate list and retrieve queries from update and close
        if self.action != "list":
            self.filterset_class = None
        qs = (
            super()
            .get_queryset()
            .filter(queue__sector__project__permissions__user=self.request.user)
        )

        last_24h = timezone.now() - timedelta(days=1)

        qs = qs.annotate(
            last_interaction=Max("messages__created_on"),
            unread_msgs=Count("messages", filter=Q(messages__seen=False)),
            last_contact_interaction=Max(
                "messages__created_on", filter=Q(messages__contact__isnull=False)
            ),
            is_24h_valid_computed=Case(
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
            last_message_text=Subquery(
                Message.objects.filter(room=OuterRef("pk"))
                .exclude(user__isnull=True, contact__isnull=True)
                .exclude(text="")
                .order_by("-created_on")
                .values("text")[:1]
            ),
        ).select_related("user", "contact", "queue", "queue__sector")

        return qs

    def get_serializer_class(self):
        if "update" in self.action:
            return TransferRoomSerializer
        elif "list" in self.action:
            return ListRoomSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["disable_has_history"] = getattr(self, "disable_has_history", False)
        return context

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        project = request.query_params.get("project")
        is_active = request.query_params.get("is_active", None)

        if isinstance(is_active, str):
            is_active = is_active.lower() == "true"

        room_status = request.query_params.get("room_status", None)

        self.disable_has_history = False

        if (
            not project
            or is_active is False
            or (room_status is not None and room_status != "ongoing")
        ):
            filtered_qs = self.filter_queryset(qs)
            return self._get_paginated_response(filtered_qs)

        project_instance = None
        use_pins_optimization = False

        if project:
            project_instance = Project.objects.filter(uuid=project).first()
            if project_instance:
                use_pins_optimization = is_feature_active(
                    settings.WENI_CHATS_PIN_ROOMS_OPTIMIZATION_FLAG_KEY,
                    request.user,
                    project_instance,
                )
                if is_feature_active(
                    settings.WENI_CHATS_DISABLE_HAS_HISTORY_FLAG_KEY,
                    request.user,
                    project_instance,
                ):
                    self.disable_has_history = True

        if use_pins_optimization:
            return self._list_with_optimized_pin_order(qs, request, project)

        return self._list_with_legacy_pin_order(qs, request, project)

    def _list_with_legacy_pin_order(self, qs, request, project):
        pins_query = {
            "room__queue__sector__project": project,
        }

        if user_email := request.query_params.get("email"):
            pins_query["user__email"] = user_email
        else:
            pins_query["user"] = request.user

        pins = RoomPin.objects.filter(**pins_query)

        pinned_rooms = Room.objects.filter(
            pk__in=pins.values_list("room__pk", flat=True)
        )

        filtered_qs = self.filter_queryset(qs)
        room_ids = set(filtered_qs.values_list("pk", flat=True)) | set(
            pinned_rooms.values_list("pk", flat=True)
        )

        secondary_sort = list(filtered_qs.query.order_by or self.ordering or [])

        pin_created_on_subquery = (
            RoomPin.objects.filter(
                user=request.user,
                room=OuterRef("pk"),
                room__queue__sector__project=project,
            )
            .order_by("-created_on")
            .values("created_on")[:1]
        )

        annotated_qs = qs.filter(pk__in=room_ids).annotate(
            is_pinned=Case(
                When(pk__in=pinned_rooms, then=True),
                default=False,
                output_field=BooleanField(),
            ),
            pin_created_on=Subquery(
                pin_created_on_subquery, output_field=DateTimeField()
            ),
        )

        if secondary_sort:
            annotated_qs = annotated_qs.order_by(
                "-is_pinned", "-pin_created_on", *secondary_sort
            )
        else:
            annotated_qs = annotated_qs.order_by("-is_pinned", "-pin_created_on")

        return self._get_paginated_response(annotated_qs)

    def _list_with_optimized_pin_order(self, qs, request, project):
        target_pins_queryset = RoomPin.objects.filter(
            room__queue__sector__project=project,
        )

        if user_email := request.query_params.get("email"):
            target_pins_queryset = target_pins_queryset.filter(user__email=user_email)
        else:
            target_pins_queryset = target_pins_queryset.filter(user=request.user)

        annotation_pins_queryset = RoomPin.objects.filter(
            room__queue__sector__project=project,
        )
        if user_email:
            annotation_pins_queryset = annotation_pins_queryset.filter(
                user__email=user_email
            )
        else:
            annotation_pins_queryset = annotation_pins_queryset.filter(
                user=request.user
            )

        pin_subquery = annotation_pins_queryset.filter(room=OuterRef("pk")).order_by(
            "-created_on"
        )
        target_pin_subquery = target_pins_queryset.filter(room=OuterRef("pk")).order_by(
            "-created_on"
        )

        annotated_qs = qs.annotate(
            is_pinned=Exists(pin_subquery),
            pin_created_on=Subquery(
                pin_subquery.values("created_on")[:1],
                output_field=DateTimeField(),
            ),
            list_is_pinned=Exists(target_pin_subquery),
            list_pin_created_on=Subquery(
                target_pin_subquery.values("created_on")[:1],
                output_field=DateTimeField(),
            ),
        )

        filtered_qs = self.filter_queryset(annotated_qs)
        filtered_room_ids = filtered_qs.values("pk").order_by()

        secondary_sort = list(filtered_qs.query.order_by or self.ordering or [])

        pinned_room_subquery = target_pins_queryset.values("room_id")

        combined_qs = annotated_qs.filter(
            Q(pk__in=Subquery(filtered_room_ids))
            | Q(pk__in=Subquery(pinned_room_subquery))
        ).distinct()

        if secondary_sort:
            combined_qs = combined_qs.order_by(
                "-is_pinned", "-pin_created_on", *secondary_sort
            )
        else:
            combined_qs = combined_qs.order_by("-is_pinned", "-pin_created_on")

        return self._get_paginated_response(combined_qs)

    def _get_paginated_response(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
        instance: Room = self.get_object()

        tags = request.data.get("tags", None)

        if tags is not None:
            sector_tags = [
                str(tag_uuid)
                for tag_uuid in SectorTag.objects.filter(
                    sector=instance.queue.sector
                ).values_list("uuid", flat=True)
            ]

            print(f"DEBUG tags: {tags}")
            print(f"DEBUG sector_tags: {sector_tags}")

            if set(tags) - set(sector_tags):
                raise ValidationError(
                    {"tags": ["Tag not found for the room's sector"]},
                    code="tag_not_found",
                )

        if instance.queue.required_tags and (not tags and not instance.tags.exists()):
            raise ValidationError(
                {"tags": ["Tags are required for this queue"]},
                code="tags_required",
            )

        if (
            instance.user is None
            and instance.queue
            and not instance.project.can_close_chats_in_queue
        ):
            permission = instance.project.get_permission(request.user)
            if not permission or not permission.is_admin:
                raise PermissionDenied(
                    detail=_(
                        "Agents cannot close queued rooms in this sector."
                    ),
                    code="queued_room_close_disabled",
                )

        with transaction.atomic():
            instance.close(tags, "agent")

        instance.refresh_from_db()
        serialized_data = RoomSerializer(instance=instance)

        instance.notify_queue("close", callback=True)
        instance.notify_user("close")

        if not settings.ACTIVATE_CALC_METRICS:
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        close_room(str(instance.pk))

        if not instance.is_billing_notified:
            instance.notify_billing()

        if instance.queue:
            logger.info(
                "Calling start_queue_priority_routing for room %s when closing it",
                instance.uuid,
            )
            start_queue_priority_routing(instance.queue)

        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_queue("create")

    def perform_update(self, serializer):
        # TODO Separate this into smaller methods
        old_instance = serializer.instance
        old_user = old_instance.user

        user = self.request.data.get("user_email")
        queue = self.request.data.get("queue_uuid")
        serializer.save()

        if not (user or queue):
            return None

        instance = serializer.instance

        # Mark all notes as non-deletable when room is transferred
        instance.mark_notes_as_non_deletable()

        # Create transfer object based on whether it's a user or a queue transfer and add it to the history
        if user:
            if old_instance.user is None:
                time = timezone.now() - old_instance.modified_on
                room_metric = RoomMetrics.objects.select_related("room").get_or_create(
                    room=instance
                )[0]
                room_metric.waiting_time += time.total_seconds()
                room_metric.queued_count += 1
                room_metric.save()
            else:
                # Get the room metric from instance and update the transfer_count value.
                room_metric = RoomMetrics.objects.select_related("room").get_or_create(
                    room=instance
                )[0]
                room_metric.transfer_count += 1
                room_metric.save()

            action = "transfer" if self.request.user.email != user else "pick"
            feedback = create_transfer_json(
                action=action,
                from_=old_instance.user or old_instance.queue,
                to=instance.user,
            )

        if queue:
            # Create constraint to make queue not none
            feedback = create_transfer_json(
                action="transfer",
                from_=old_instance.user or old_instance.queue,
                to=instance.queue,
            )
            if (
                not user
            ):  # if it is only a queue transfer from a user, need to reset the user field
                instance.user = None

            room_metric = RoomMetrics.objects.select_related("room").get_or_create(
                room=instance
            )[0]
            room_metric.transfer_count += 1
            room_metric.save()

        instance.save()
        instance.add_transfer_to_history(feedback)

        # Create a message with the transfer data and Send to the room group
        # TODO separate create message in a function
        create_room_feedback_message(
            instance, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
        )

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

    @action(
        detail=True,
        methods=["POST", "GET"],
        url_name="chat_completion",
    )
    def chat_completion(self, request, *args, **kwargs) -> Response:
        user_token = request.META.get("HTTP_AUTHORIZATION")
        room = self.get_object()
        if request.method == "GET":
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "can_use_chat_completion": room.queue.sector.can_use_chat_completion
                },
            )
        if not room.queue.sector.can_use_chat_completion:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"detail": "Chat completion is not configured for this sector."},
            )
        token = room.queue.sector.project.get_openai_token(user_token)
        if not token:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"detail": "OpenAI token not found"},
            )
        messages = room.last_5_messages
        if not messages:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"detail": "The selected room does not have messages"},
            )
        serialized_data = ChatCompletionSerializer(messages, many=True).data

        sector = room.queue.sector
        if sector.completion_context:
            serialized_data.append(
                {"role": "system", "content": sector.completion_context}
            )

        openai_client = OpenAIClient()
        completion_response = openai_client.chat_completion(
            token=token, messages=serialized_data
        )
        return Response(
            status=completion_response.status_code, data=completion_response.json()
        )

    @action(
        detail=True,
        methods=["PATCH"],
    )
    def update_custom_fields(self, request, pk=None):
        custom_fields_update = request.data
        data = {"fields": custom_fields_update}

        if pk is None:
            return Response(
                {"Detail": "No room on the request"}, status.HTTP_400_BAD_REQUEST
            )
        elif not custom_fields_update:
            return Response(
                {"Detail": "No custom fields on the request"},
                status.HTTP_400_BAD_REQUEST,
            )

        room = get_editable_custom_fields_room({"uuid": pk, "is_active": "True"})

        custom_field_name = list(data["fields"])[0]
        old_custom_field_value = room.custom_fields.get(custom_field_name, None)
        new_custom_field_value = data["fields"][custom_field_name]

        update_flows_custom_fields(
            project=room.queue.sector.project,
            data=data,
            contact_id=room.contact.external_id,
        )

        update_custom_fields(room, custom_fields_update)

        feedback = {
            "user": request.user.first_name,
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

    @action(
        detail=True,
        methods=[
            "PATCH",
        ],
        url_name="pick_queue_room",
    )
    def pick_queue_room(self, request, *args, **kwargs):
        room: Room = self.get_object()
        user: User = request.user

        logger.info(
            f"[PICK_QUEUE_ROOM] Starting room pick - Room: {room.uuid}, "
            f"User: {user.email}, Queue: {room.queue.name if room.queue else 'None'}"
        )

        if room.user:
            logger.warning(
                f"[PICK_QUEUE_ROOM] Room already assigned - Room: {room.uuid}, "
                f"Current User: {room.user.email}, Requested User: {user.email}"
            )
            raise ValidationError(
                {"detail": _("Room is not queued")}, code="room_is_not_queued"
            )

        action = "pick"
        feedback = create_transfer_json(
            action=action,
            from_=room.queue,
            to=user,
        )

        try:
            room.user = user
            room.save()
            room.add_transfer_to_history(feedback)

            create_room_feedback_message(
                room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
            )
            room.notify_queue("update")

            room.send_automatic_message()

            room_metric = RoomMetrics.objects.select_related("room").get_or_create(
                room=room
            )[0]
            room_metric.waiting_time += calculate_last_queue_waiting_time(room)
            room_metric.queued_count += 1
            room_metric.save()

            # Use async ticket update to avoid blocking the response
            room.update_ticket_async()

            return Response(
                {
                    "detail": _("Room picked successfully"),
                    "room_uuid": str(room.uuid),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.error(
                f"[PICK_QUEUE_ROOM] Error during room pick - Room: {room.uuid}, "
                f"User: {user.email}, Error: {str(exc)}"
            )
            raise

    @action(
        detail=False,
        methods=["PATCH"],
        url_name="bulk_transfer",
    )
    def bulk_transfer(self, request, pk=None):
        rooms_list = Room.objects.filter(
            uuid__in=request.data.get("rooms_list")
        ).select_related("user", "queue__sector__project")
        user_email = request.query_params.get("user_email")
        queue_uuid = request.query_params.get("queue_uuid")
        user_request = request.user or request.query_params.get("user_request")

        if not user_email and not queue_uuid:
            return Response(
                {"error": "user_email or queue_uuid is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_email and queue_uuid:
            user = User.objects.get(email=user_email)
            queue = Queue.objects.get(uuid=queue_uuid)

            projects = rooms_list.values_list(
                "queue__sector__project__uuid", flat=True
            ).distinct()

            for project in projects:
                if project != queue.project.uuid:
                    return Response(
                        {"error": "Cannot transfer rooms from a project to another"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            for room in rooms_list:
                old_queue = room.queue
                old_user = room.user

                room.queue = queue
                room.user = user

                room.save()

                feedback_queue = create_transfer_json(
                    action="transfer",
                    from_=old_queue,
                    to=queue,
                )
                feedback_user = create_transfer_json(
                    action="transfer",
                    from_=old_user,
                    to=user,
                )
                create_room_feedback_message(
                    room, feedback_queue, method=RoomFeedbackMethods.ROOM_TRANSFER
                )
                create_room_feedback_message(
                    room, feedback_user, method=RoomFeedbackMethods.ROOM_TRANSFER
                )
                room.notify_queue("update")
                room.notify_user("update", user=old_user)
                room.notify_user("update")

                start_queue_priority_routing(queue)

                room.mark_notes_as_non_deletable()
                room.update_ticket_async()

        elif user_email and not queue_uuid:
            email_l = (user_email or "").lower()
            uid = get_user_id_by_email_cached(email_l)

            if uid is None:
                return Response(
                    {"error": f"User {user_email} not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = User.objects.get(pk=uid)

            for room in rooms_list:
                old_user = room.user
                project = room.queue.project
                if not project.permissions.filter(user=user).exists():
                    return Response(
                        {
                            "error": (
                                f"User {user.email} has no permission on the project "
                                f"{project.name} <{project.uuid}>"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                transfer_user = verify_user_room(room, user_request)

                feedback = create_transfer_json(
                    action="transfer",
                    from_=transfer_user,
                    to=user,
                )

                old_user_assigned_at = room.user_assigned_at

                room.user = user
                room.save()

                logger.info(
                    "Starting queue priority routing for room %s from bulk transfer to user %s",
                    room.uuid,
                    user.email,
                )
                start_queue_priority_routing(room.queue)

                create_room_feedback_message(
                    room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
                )
                if old_user:
                    room.notify_user("update", user=old_user)
                else:
                    room.notify_user("update", user=transfer_user)
                room.notify_user("update")
                room.notify_queue("update")

                room.update_ticket()
                room.mark_notes_as_non_deletable()
                if (
                    not old_user_assigned_at
                    and room.queue.sector.is_automatic_message_active
                    and room.queue.sector.automatic_message_text
                ):
                    room.send_automatic_message()

        elif queue_uuid and not user_email:
            queue = Queue.objects.get(uuid=queue_uuid)
            for room in rooms_list:
                if queue.project != room.project:
                    return Response(
                        {"error": "Cannot transfer rooms from a project to another"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                transfer_user = verify_user_room(room, user_request)
                feedback = create_transfer_json(
                    action="transfer",
                    from_=transfer_user,
                    to=queue,
                )
                room.user = None
                room.queue = queue
                room.save()

                create_room_feedback_message(
                    room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
                )
                room.notify_user("update", user=transfer_user)
                room.notify_queue("update")

                logger.info(
                    "Starting queue priority routing for room %s from bulk transfer to queue %s",
                    room.uuid,
                    queue.uuid,
                )
                start_queue_priority_routing(queue)

                # Mark all notes as non-deletable when room is transferred
                room.mark_notes_as_non_deletable()

        return Response(
            {"success": "Mass transfer completed"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="human-service-count")
    def filter_rooms(self, request, pk=None):
        project_uuid = request.query_params.get("project_uuid")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not project_uuid:
            return Response({"error": "'project_uuid' is required."}, status=400)

        default_start_date = timezone.now() - timedelta(days=30)
        default_end_date = timezone.now()

        try:
            if start_date:
                start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
            else:
                start_date = default_start_date

            if end_date:
                end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d"))
            else:
                end_date = default_end_date
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use 'YYYY-MM-DD'."}, status=400
            )

        rooms = Room.objects.filter(
            queue__sector__project=project_uuid,
            created_on__gte=start_date,
            created_on__lte=end_date,
        )

        room_count = rooms.count()
        return Response({"room_count": room_count})

    @action(
        detail=False,
        methods=["get"],
        url_name="rooms-info",
        serializer_class=RoomInfoSerializer,
    )
    def rooms_info(self, request: Request, pk=None) -> Response:
        project_uuid = request.query_params.get("project_uuid")

        if not project_uuid:
            return Response(
                {"error": "'project_uuid' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        query = {"project_uuid": project_uuid}

        if uuid := request.query_params.get("uuid"):
            query["uuid"] = uuid

        rooms = self.paginate_queryset(
            Room.objects.filter(**query).order_by("-created_on")
        )

        return Response(
            RoomInfoSerializer(rooms, many=True).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get"], url_path="chats-summary")
    def chats_summary(self, request: Request, pk=None) -> Response:
        """
        Get the history summary for a room.
        """
        room = self.get_object()

        history_summary = (
            HistorySummary.objects.filter(room=room).order_by("created_on").last()
        )

        if not history_summary:
            return Response(
                {
                    "status": HistorySummaryStatus.UNAVAILABLE,
                    "summary": None,
                    "feedback": {"liked": None},
                },
                status=status.HTTP_200_OK,
            )

        serializer = RoomHistorySummarySerializer(
            history_summary, context={"request": request}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_name="chats-summary-feedback",
        url_path="chats-summary/feedback",
        serializer_class=RoomHistorySummaryFeedbackSerializer,
    )
    def chats_summary_feedback(self, request: Request, pk=None) -> Response:
        """
        Get the history summary for a room.
        """
        room = self.get_object()

        history_summary = (
            HistorySummary.objects.filter(room=room).order_by("created_on").last()
        )

        if not history_summary:
            raise NotFound({"detail": "No history summary found for this room."})

        if history_summary.room.user != request.user:
            raise PermissionDenied(
                {"detail": "You are not allowed to give feedback for this room."},
                code="user_is_not_the_room_user",
            )

        if history_summary.status != HistorySummaryStatus.DONE:
            raise ValidationError(
                {
                    "detail": "You can only give feedback when the history summary is done."
                },
                code="room_history_summary_not_done",
            )

        serializers_params = {
            "data": request.data,
            "context": {"request": request, "history_summary": history_summary},
        }

        if existing_feedback := history_summary.feedbacks.filter(
            user=request.user
        ).first():
            serializers_params["instance"] = existing_feedback

        serializer = RoomHistorySummaryFeedbackSerializer(
            **serializers_params,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_name="pin",
        url_path="pin",
        serializer_class=PinRoomSerializer,
    )
    def pin(self, request: Request, pk=None) -> Response:
        serializer = PinRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room: Room = self.get_object()
        user: User = request.user

        method = (
            room.pin if serializer.validated_data.get("status") is True else room.unpin
        )

        try:
            method(user)
        except (
            MaxPinRoomLimitReachedError,
            RoomIsNotActiveError,
        ) as e:
            raise ValidationError(e.to_dict(), code=e.code) from e
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="room_note",
        serializer_class=RoomNoteSerializer,
    )
    def create_note(self, request, pk=None):
        """
        Create a note for the room
        """
        room = self.get_object()

        # Verify user has access to the room
        if not verify_user_room(room, request.user):
            raise PermissionDenied(
                "You don't have permission to add notes to this room"
            )

        # Room must be active
        if not room.is_active:
            raise ValidationError({"detail": "Cannot add notes to closed rooms"})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create a blank message to attach the internal note
        msg = Message.objects.create(
            room=room,
            user=request.user,
            contact=None,
            text="",
        )

        # Create the note attached to the message
        note = RoomNote.objects.create(
            room=room,
            user=request.user,
            text=serializer.validated_data["text"],
            message=msg,
        )

        # Notify message creation for clients listening to messages
        msg.notify_room("create", True)

        # Return serialized note
        return Response(RoomNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get"],
        url_path="tags",
        serializer_class=RoomTagSerializer,
    )
    def tags(self, request: Request, pk=None) -> Response:
        room: Room = self.get_object()

        tags = room.tags.all()

        page = self.paginate_queryset(tags)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(tags, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="tags/add",
        url_name="add-tag",
        serializer_class=AddRoomTagSerializer,
        permission_classes=[IsAuthenticated, CanAddOrRemoveRoomTagPermission],
    )
    def add_tag(self, request: Request, pk=None) -> Response:
        room: Room = self.get_object()

        if not room.is_active:
            raise ValidationError(
                {"detail": "Room is not active."},
                code="room_is_not_active",
            )

        if not room.user or not room.user == request.user:
            raise PermissionDenied(
                {"detail": "You are not allowed to add tags to this room."},
                code="user_is_not_the_room_user",
            )

        serializer = self.get_serializer(data=request.data, context={"room": room})
        serializer.is_valid(raise_exception=True)

        sector_tag = serializer.validated_data.get("sector_tag")
        room.tags.add(sector_tag)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="tags/remove",
        url_name="remove-tag",
        serializer_class=RemoveRoomTagSerializer,
        permission_classes=[IsAuthenticated, CanAddOrRemoveRoomTagPermission],
    )
    def remove_tag(self, request: Request, pk=None) -> Response:
        room: Room = self.get_object()

        if not room.is_active:
            raise ValidationError(
                {"detail": "Room is not active."},
                code="room_is_not_active",
            )

        if not room.user or not room.user == request.user:
            raise PermissionDenied(
                {"detail": "You are not allowed to remove tags from this room."},
                code="user_is_not_the_room_user",
            )

        serializer = self.get_serializer(data=request.data, context={"room": room})
        serializer.is_valid(raise_exception=True)
        sector_tag = serializer.validated_data.get("sector_tag")
        room.tags.remove(sector_tag)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="room_note",
        serializer_class=RoomNoteSerializer,
    )
    def create_note(self, request, pk=None):
        """
        Create a note for the room
        """
        room = self.get_object()

        # Verify user has access to the room
        if not verify_user_room(room, request.user):
            raise PermissionDenied(
                "You don't have permission to add notes to this room"
            )

        # Room must be active
        if not room.is_active:
            raise ValidationError({"detail": "Cannot add notes to closed rooms"})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create a blank message to attach the internal note
        msg = Message.objects.create(
            room=room,
            user=request.user,
            contact=None,
            text="",
        )

        # Create the note attached to the message
        note = RoomNote.objects.create(
            room=room,
            user=request.user,
            text=serializer.validated_data["text"],
            message=msg,
        )

        # Notify message creation for clients listening to messages
        msg.notify_room("create", True)

        # Return serialized note
        return Response(RoomNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get"],
        url_path="can-send-message-status",
        url_name="can-send-message-status",
    )
    def can_send_message_status(self, request, pk=None):
        """
        Check if the user can send a message to the room
        """

        room: Room = self.get_object()

        response = {"can_send_message": room.is_24h_valid}

        return Response(response, status=status.HTTP_200_OK)


class RoomsReportViewSet(APIView):
    """
    Viewset for generating rooms reports.
    """

    authentication_classes = [ProjectAdminAuthentication]
    service = RoomsReportService

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        Generate a rooms report and send it to the email address provided.
        """
        if not request.auth:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        project_uuid = request.auth.project
        project = Project.objects.get(uuid=project_uuid)

        service = self.service(project)

        if service.is_generating_report():
            return Response(
                {
                    "detail": "A report is already being generated for this project. Please wait for it to finish."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = RoomsReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_email = serializer.validated_data.get("recipient_email")
        rooms_filters = serializer.validated_data.get("filters")

        generate_rooms_report.delay(project.uuid, rooms_filters, recipient_email)

        return Response(
            {
                "detail": "The report will be sent to the email address provided when it's ready."
            },
            status=status.HTTP_202_ACCEPTED,
        )


class RoomNoteViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """
    ViewSet for Room Notes
    """

    queryset = RoomNote.objects.all()
    serializer_class = RoomNoteSerializer
    permission_classes = [permissions.IsAuthenticated, RoomNotePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["room"]
    lookup_field = "uuid"

    def get_queryset(self):
        """
        Filter notes based on user permissions
        """
        user = self.request.user
        queryset = super().get_queryset()

        room_uuid = self.request.query_params.get("room")
        if room_uuid:
            queryset = queryset.filter(room__uuid=room_uuid)

        return (
            queryset.filter(
                Q(room__user=user)
                | Q(room__queue__sector__project__permissions__user=user)
            )
            .distinct()
            .order_by("created_on")
        )

    def list(self, request, *args, **kwargs):
        """
        List room notes with additional validations
        """

        room_uuid = request.query_params.get("room")
        if not room_uuid:
            raise ValidationError({"detail": "Room UUID is required"})

        if not Room.objects.filter(uuid=room_uuid).exists():
            raise ValidationError({"detail": "Room not found"})

        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a room note with validations
        """
        note = self.get_object()

        if not note.is_deletable:
            raise ValidationError(
                {"Note cannot be deleted because it was marked as non-deletable"}
            )

        if note.user != request.user:
            raise PermissionDenied("You can only delete your own notes")

        # Sala aberta
        if not note.room.is_active:
            raise ValidationError({"detail": "Cannot delete notes from closed rooms"})

        note.notify_websocket("delete")

        return super().destroy(request, *args, **kwargs)
