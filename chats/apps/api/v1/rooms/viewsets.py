from django.utils.translation import gettext_lazy as _
from djongo.models import Q
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1.rooms.serializers import (RoomSerializer,
                                                 TransferRoomSerializer)
from chats.apps.rooms.models import Room


class RoomViewset(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def list(self, request, *args, **kwargs):
        """
        Return user related rooms and rooms related to the sectors the user is in what are empty of a user
        """
        rooms = Room.objects.filter(
            Q(user=request.user) | Q(user__isnull=True),
            sector__id__in=request.user.sector_ids,
            is_active=True,
        )

        return rooms

    def update(
        self, request, *args, **kwargs
    ):  # TODO: Config swagger to show the fields related the serializer below
        """
        Update the user and/or the sector of the room, but only if the user is the agent related to the room
        """
        self.serializer_class = TransferRoomSerializer
        return super().update(request, *args, **kwargs)

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
        instance.close(tags)
        serialized_data = RoomSerializer(instance=instance)
        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")
        super().perform_destroy(instance)
