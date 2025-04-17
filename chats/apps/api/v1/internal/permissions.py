from rest_framework import permissions


class ModuleHasPermission(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no covers
        return request.user.has_perm("accounts.can_communicate_internally")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
