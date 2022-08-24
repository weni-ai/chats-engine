from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions

from chats.apps.rooms.models import Room


class MessagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ["list", "create"]:
            room = Room.objects.get(uuid=request.data.get("room"))
            return room.user == request.user

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, message) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False

        return message.room.user == request.user


class MessageMediaPermission(permissions.BasePermission):
    """ """

    def has_permission(self, request, view):
        if view.action == "create":
            room = Room.objects.get(messages__uuid=request.data.get("message"))
            return room.user == request.user
        elif view.action == "list":
            room = Room.objects.get(uuid=request.query_params.get("room"))
            return room.user == request.user
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False

        return obj.message.room.user == request.user
