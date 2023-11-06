from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from chats.apps.rooms.models import Room


class DiscussionObjectPermissionActions:
    def __init__(self, request, obj) -> None:
        self.request = request
        self.obj = obj
        self.user = self.request.user

    def retrieve(self):
        return self.obj.can_retrieve(self.user)

    def destroy(self):
        return self.obj.is_admin_manager_or_creator(self.user)

    def list_agents(self):
        return self.retrieve()

    def add_agents(self):
        if self.obj.is_admin_manager_or_creator(self.user):
            return True
        if self.obj.added_users.count() < 2:
            user_email = self.request.data.get("user_email")
            return user_email == self.user.email


class CanManageDiscussion(permissions.BasePermission):
    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False
        if view.action == "create":
            try:
                room = request.data.get("room")
                room = Room.objects.get(pk=room)
                return room.can_create_discussion(user=request.user)
            except Exception:
                return False

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        action_permissions = DiscussionObjectPermissionActions(request=request, obj=obj)
        try:
            return getattr(action_permissions, view.action)()

        except AttributeError:
            return obj.can_retrieve(request.user)
