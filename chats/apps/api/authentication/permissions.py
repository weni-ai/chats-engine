from rest_framework.permissions import BasePermission


class JWTRequiredPermission(BasePermission):
    """
    Custom permission class that requires JWT authentication.
    Returns 401 Unauthorized when authentication fails.
    """

    def has_permission(self, request, view):
        return request.auth is not None


class InternalAPITokenRequiredPermission(BasePermission):
    """
    Custom permission class that requires Internal API token authentication.
    Returns 401 Unauthorized when authentication fails.
    """

    def has_permission(self, request, view):
        return getattr(request, "auth", None) == "INTERNAL"
