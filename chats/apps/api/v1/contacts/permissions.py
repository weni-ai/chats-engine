from rest_framework import permissions


class ContactRelatedRetrievePermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        """
        Only used on retrieve methods
        """
        return obj.can_retrieve(request.user, request.query_params.get("project"))
