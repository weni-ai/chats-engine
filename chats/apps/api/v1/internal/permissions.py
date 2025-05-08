from django.conf import settings
from django_redis import get_redis_connection
from rest_framework import permissions


class ModuleHasPermission(permissions.BasePermission):
    cache_ttl = settings.INTERNAL_CLIENTS_PERM_CACHE_TTL

    def has_permission(self, request, view):  # pragma: no cover
        redis_connection = get_redis_connection()

        cache_key = f"internal_client_perm:{request.user.id}"

        if redis_connection.get(cache_key):
            return True

        has_perm = request.user.has_perm("accounts.can_communicate_internally")

        if has_perm:
            redis_connection.set(cache_key, has_perm, self.cache_ttl)

        return has_perm

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
