import json
import logging
import re
import time
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django_redis import get_redis_connection
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from chats.apps.accounts.models import User

LOGGER = logging.getLogger("weni_django_oidc")


class UserEmailCache:
    """
    Cache de usuários por email (CACHE 2).
    Cacheia: Email → User do banco
    """
    
    CACHE_PREFIX = "user:email:"
    CACHE_TTL = settings.USER_EMAIL_CACHE_TTL  # Vem do settings/env
    
    @classmethod
    def get_cache_key(cls, email: str) -> str:
        """Gera chave de cache normalizada."""
        return f"{cls.CACHE_PREFIX}{email.lower()}"
    
    @classmethod
    def get_user(cls, email: str) -> Optional['User']:
        """Busca usuário do cache por email."""
        if not email:
            return None
            
        cache_key = cls.get_cache_key(email)
        cached_user = cache.get(cache_key)
        
        if cached_user:
            LOGGER.debug(f"Email cache HIT for: {email}")
        else:
            LOGGER.debug(f"Email cache MISS for: {email}")
            
        return cached_user
    
    @classmethod
    def set_user(cls, email: str, user: 'User') -> None:
        """Armazena usuário no cache."""
        if not email or not user:
            return
            
        cache_key = cls.get_cache_key(email)
        cache.set(cache_key, user, cls.CACHE_TTL)
        LOGGER.debug(f"User cached for email: {email}")
    
    @classmethod
    def invalidate(cls, email: str) -> None:
        """Remove usuário do cache."""
        if not email:
            return
            
        cache_key = cls.get_cache_key(email)
        cache.delete(cache_key)


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
        # validação de permissão
        verified = super(WeniOIDCAuthenticationBackend, self).verify_claims(claims)
        # is_admin = "admin" in claims.get("roles", [])
        return verified  # and is_admin # not checking for user roles from keycloak at this time

    def get_username(self, claims):
        username = claims.get("preferred_username")
        if username:
            return username
        return super(WeniOIDCAuthenticationBackend, self).get_username(claims=claims)

    def create_user(self, claims):
        # Override existing create_user method in OIDCAuthenticationBackend
        email = claims.get("email")
        
        # CACHE 2: Tenta buscar do cache de emails primeiro
        cached_user = UserEmailCache.get_user(email)
        if cached_user:            
            # Atualiza dados se necessário
            updated = False
            first_name = claims.get("given_name", "")
            last_name = claims.get("family_name", "")
            
            if cached_user.first_name != first_name:
                cached_user.first_name = first_name
                updated = True
            
            if cached_user.last_name != last_name:
                cached_user.last_name = last_name
                updated = True
            
            if updated:
                cached_user.save(update_fields=['first_name', 'last_name'])
            
            check_module_permission(claims, cached_user)
            return cached_user
        
        username = self.get_username(claims)[:16]
        username = re.sub("[^A-Za-z0-9]+", "", username)
        
        # Esta é a query SQL que você quer evitar!
        user = User.objects.get_or_create(email=email)[0]

        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        check_module_permission(claims, user)
        
        # Armazena no CACHE 2 após criar/buscar
        UserEmailCache.set_user(email, user)        
        return user
