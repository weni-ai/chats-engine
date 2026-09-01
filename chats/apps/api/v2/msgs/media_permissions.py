from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from chats.apps.rooms.models import Room


class MessageMediaCreatePermissionV2(permissions.BasePermission):
    """
    Only the agent assigned to the room can upload media for it.
    """

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False

        if view.action != "create":
            return False

        room_uuid = request.data.get("room")
        if not room_uuid:
            return False

        room = Room.objects.filter(uuid=room_uuid).first()
        if room is None:
            return False

        return room.user == request.user
