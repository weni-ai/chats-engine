from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.rooms.serializers import RoomFlowSerializer
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import (
    close_room,
    create_room_feedback_message,
    create_transfer_json,
    get_editable_custom_fields_room,
    update_custom_fields,
    update_flows_custom_fields,
)


def add_user_or_queue_to_room(instance, request):
    # TODO Separate this into smaller methods
    user = request.data.get("user_email")
    queue = request.data.get("queue_uuid")

    # TODO create json to action forward in this code above
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
    create_room_feedback_message(instance, feedback, method="rt")

    # Create a message with the transfer data and Send to the room group
    create_room_feedback_message(instance, feedback, method="rt")

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
        if not settings.ACTIVATE_CALC_METRICS:
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        close_room(str(instance.pk))
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
        try:
            room = Room.objects.get(
                callback_url__endswith=pk,
                queue__sector__project=project,
                is_active=True,
            )
        except (Room.DoesNotExist, ValidationError):
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

        create_room_feedback_message(room, feedback, method="rt")

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
        # TODO create message for edit custom field in this code above

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
            project=room.queue.sector.project,
            data=data,
            contact_id=room.contact.external_id,
        )

        update_custom_fields(room, custom_fields_update)

        feedback = {
            "user": request_permission.user.first_name,
            "custom_field_name": custom_field_name,
            "old": old_custom_field_value,
            "new": new_custom_field_value,
        }

        create_room_feedback_message(room, feedback, method="ecf")

        return Response(
            {"Detail": "Custom Field edited with success"},
            status.HTTP_200_OK,
        )
