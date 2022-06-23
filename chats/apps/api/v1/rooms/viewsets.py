from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from chats.apps.api.v1.rooms.serializers import RoomSerializer
from chats.apps.rooms.models import Room


class RoomViewset(viewsets.ModelViewSet):
    queryset = Room.objects
    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticated,
    ]
