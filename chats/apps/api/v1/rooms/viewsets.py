from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from chats.apps.api.v1.rooms.serializers import RoomSerializer
from chats.apps.rooms.models import Room


class RoomViewset(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")
        super().perform_destroy(instance)
