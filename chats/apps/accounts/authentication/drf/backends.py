import json
import logging
import re

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django_redis import get_redis_connection
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from chats.apps.accounts.models import User
from chats.core.cache_utils import get_cached_user, invalidate_cached_user

LOGGER = logging.getLogger("weni_django_oidc")


def check_module_permission(claims, user):
    if claims.get("can_communicate_internally", False):
        content_type = ContentType.objects.get_for_model(User)
        permission, created = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            name="can communicate internally",
            content_type=content_type,
        )
        if not user.has_perm("accounts.can_communicate_internally"):
            user.user_permissions.add(permission)
        return True
    return False


class WeniOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    cache_token = settings.OIDC_CACHE_TOKEN
    cache_ttl = settings.OIDC_CACHE_TTL
    internal_token_cache_ttl = settings.OIDC_INTERNAL_TOKEN_CACHE_TTL

    def get_userinfo(self, access_token, *args):
        """
        Cache OIDC token userinfo to avoid external calls to Keycloak
        """
        if not self.cache_token:
            return super().get_userinfo(access_token, *args)

        redis_connection = get_redis_connection()

        userinfo = redis_connection.get(access_token)

        if userinfo is not None:
            return json.loads(userinfo)

        userinfo = super().get_userinfo(access_token, *args)

        can_communicate_internally = userinfo.get("can_communicate_internally", False)

        # Internal clients tokens have a longer cache time
        cache_ttl = (
            self.internal_token_cache_ttl
            if can_communicate_internally
            else self.cache_ttl
        )

        redis_connection.set(access_token, json.dumps(userinfo), cache_ttl)

        return userinfo

    def verify_claims(self, claims):
        verified = super(WeniOIDCAuthenticationBackend, self).verify_claims(claims)
        return verified

    def get_username(self, claims):
        username = claims.get("preferred_username")
        if username:
            return username
        return super(WeniOIDCAuthenticationBackend, self).get_username(claims=claims)

    def get_or_create_user(self, access_token, id_token, payload):
        """
        Override complete method to use cache and avoid filter_users_by_claims query.
        This eliminates the expensive UPPER(email) database query on every request.
        """
        # Get userinfo from token (uses cache if enabled)
        user_info = self.get_userinfo(access_token, id_token, payload)
        claims = self.get_claims(access_token, id_token, user_info)
        
        email = claims.get('email')
        if not email:
            return None
        
        # Try to get user from cache first - NO DATABASE QUERY
        user = get_cached_user(email)
        
        if user:
            # User found in cache - update and return
            user.first_name = claims.get("given_name", "")
            user.last_name = claims.get("family_name", "")
            user.save()
            
            # Invalidate cache after update to ensure fresh data on next request
            invalidate_cached_user(email)
            check_module_permission(claims, user)
            
            return user
        
        # Cache miss - get or create from database
        user, created = self.UserModel.objects.get_or_create(email=email)
        
        # Update user information from claims
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()
        
        # Invalidate cache to populate on next request
        invalidate_cached_user(email)
        check_module_permission(claims, user)
        
        if created:
            LOGGER.info(f"Created new user: {email}")
        
        return user

    def create_user(self, claims):
        """
        Fallback method - kept for compatibility but not used when get_or_create_user is overridden.
        This method was causing redundant queries, now handled by get_or_create_user with cache.
        """
        email = claims.get("email")
        
        user = get_cached_user(email)
        
        if not user:
            user = self.UserModel.objects.create(email=email)
        
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()
        
        invalidate_cached_user(email)
        check_module_permission(claims, user)
        
        return user