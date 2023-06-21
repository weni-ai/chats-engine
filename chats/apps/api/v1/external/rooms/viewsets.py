import json

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
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.dashboard.models import RoomMetrics
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

        transfer_history = room.transfer_history or []

        transfer_content = {"type": "user", "name": room.user.full_name}
        transfer_history.append(transfer_content)
        room.save()

        room.notify_user("update", user=None)
        room.notify_queue("update")

        msg = room.messages.create(text=json.dumps(transfer_content), seen=True)
        msg.notify_room("create")

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
    permission_classes = [
        IsAdminPermission,
    ]
    authentication_classes = [ProjectAdminAuthentication]

    def partial_update(self, request, pk=None):
        custom_fields_update = request.data
        data = {"fields": custom_fields_update}

        if pk is None:
            return Response(
                {"Detail": "No contact id on the request"}, status.HTTP_400_BAD_REQUEST
            )
        request_permission = self.request.auth
        project = request_permission.project

        response = FlowRESTClient().create_contact(
            project=project, data=data, contact_id=pk
        )
        if response.status_code not in [status.HTTP_200_OK]:
            return Response(
                {
                    "Detail": f"[{response.status_code}]\n"
                    + f"Error updating custom fields on flows. Exception: {response.content}"
                },
                status.HTTP_404_NOT_FOUND,
            )

        room = Room.objects.filter(
            contact__external_id=pk,
            queue__sector__project=project,
            is_active=True,
        ).update(custom_fields=custom_fields_update)

        if not room:
            return Response(
                {
                    "Detail": "Contact with the given id was not found, it does not exist or it is deleted"
                },
                status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"Detail": "Custom Field edited with success"},
            status.HTTP_200_OK,
        )
