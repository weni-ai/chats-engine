from rest_framework.permissions import BasePermission


class IsExternalProject(BasePermission):
    def has_permission(self, request, view):
        return request.auth and request.auth.project
