import logging
from django.conf import settings
from django_redis import get_redis_connection
from rest_framework import permissions


LOGGER = logging.getLogger("weni_django_oidc")


class ModuleHasPermission(permissions.BasePermission):
    cache_ttl = settings.INTERNAL_CLIENTS_PERM_CACHE_TTL

    def has_permission(self, request, view):  # pragma: no cover
        if request.user.is_anonymous:
            return False

        redis_connection = get_redis_connection()

        LOGGER.info(
            "Checking if user %s has permission to communicate internally",
            request.user.email,
        )

        LOGGER.info("Getting cached value for user %s", request.user.email)

        cache_key = f"internal_client_perm:{request.user.id}"

        try:
            cached_value = redis_connection.get(cache_key).decode()
        except Exception:
            cache_key = None

        if cached_value is not None and cached_value == "true":
            LOGGER.info(
                "Cached value found for user %s, the user has permission to communicate internally",
                request.user.email,
            )
            return True

        LOGGER.info(
            "No cached value found for user %s or user does not have permission to communicate internally",
            request.user.email,
        )

        has_perm = request.user.has_perm("accounts.can_communicate_internally")

        if has_perm:
            redis_connection.set(cache_key, "true", self.cache_ttl)

        return has_perm

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
