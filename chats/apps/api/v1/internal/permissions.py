from django.conf import settings
from django_redis import get_redis_connection
from rest_framework import permissions


class ModuleHasPermission(permissions.BasePermission):
    cache_ttl = settings.INTERNAL_CLIENTS_PERM_CACHE_TTL

    def has_permission(self, request, view):  # pragma: no cover
        if request.user.is_anonymous:
            return False

        redis_connection = get_redis_connection()

        cache_key = f"internal_client_perm:{request.user.id}"
        cached_value = redis_connection.get(cache_key)

        if cached_value is not None:
            if isinstance(cached_value, bytes):
                cached_value = cached_value.decode()

            if cached_value == "true":
                return True

        has_perm = request.user.has_perm("accounts.can_communicate_internally")

        if has_perm:
            redis_connection.set(cache_key, "true", self.cache_ttl)

        return has_perm

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
