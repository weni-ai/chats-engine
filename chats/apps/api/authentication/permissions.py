from rest_framework.permissions import BasePermission


class JWTRequiredPermission(BasePermission):
    """
    Custom permission class that requires JWT authentication.
    Returns 401 Unauthorized when authentication fails.
    """

    def has_permission(self, request, view):
        return request.auth is not None
