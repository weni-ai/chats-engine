from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions

from chats.apps.api.v1 import WRITE_METHODS
from chats.apps.rooms.models import Room


class MessagePermission(permissions.BasePermission):
    """ """

    def has_permission(self, request, view):
        if request.method in WRITE_METHODS:
            room = Room.objects.get(uuid=request.data.get("room"))
            return room.user == request.user

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(request.user)
        except ObjectDoesNotExist:
            return False
        return authorization.is_agent(str(obj.queue.pk))


class MessageMediaPermission(permissions.BasePermission):
    """ """

    def has_permission(self, request, view):
        if request.method in WRITE_METHODS:
            room = Room.objects.get(messages__uuid=request.data.get("message"))
            return room.user == request.user

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(request.user)
        except ObjectDoesNotExist:
            return False
        return authorization.is_authorized
