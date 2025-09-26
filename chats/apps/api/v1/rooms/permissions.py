from rest_framework.permissions import BasePermission


class CanAddOrRemoveRoomTagPermission(BasePermission):

    def has_object_permission(self, request, view, obj):
        room_user = getattr(obj, "user", None)

        if not room_user:
            return False

        return room_user == request.user
