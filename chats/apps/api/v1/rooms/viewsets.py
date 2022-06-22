from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, permissions, mixins, viewsets, pagination
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from chats.apps.api.v1.rooms.serializers import RoomSerializer
from chats.apps.rooms.models import Room


class RoomViewset(viewsets.ModelViewSet):
    queryset = Room.objects
    serializer_class = RoomSerializer
