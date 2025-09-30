from rest_framework.permissions import BasePermission


class CSATWebhookPermission(BasePermission):
    def has_permission(self, request, view):
        # TODO: Add permission logic
        return True
