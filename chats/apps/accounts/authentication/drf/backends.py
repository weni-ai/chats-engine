import json
import logging
import re

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django_redis import get_redis_connection
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from chats.apps.accounts.models import User

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

    def get_userinfo(self, access_token, *args):
        if not self.cache_token:
            return super().get_userinfo(access_token, *args)

        redis_connection = get_redis_connection()

        userinfo = redis_connection.get(access_token)

        if userinfo is not None:
            return json.loads(userinfo)

        userinfo = super().get_userinfo(access_token, *args)
        redis_connection.set(access_token, json.dumps(userinfo), self.cache_ttl)

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
        username = self.get_username(claims)[:16]
        username = re.sub("[^A-Za-z0-9]+", "", username)
        user = self.UserModel.objects.get_or_create(email=email)[0]

        user.name = claims.get("name", "")
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        check_module_permission(claims, user)

        return user
