from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

from chats.apps.accounts.authentication.drf.backends import (
    WeniOIDCAuthenticationBackend,
)


@database_sync_to_async
def get_user(token_key):
    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


@database_sync_to_async
def get_keycloak_user(token_key):
    auth = WeniOIDCAuthenticationBackend()
    return auth.get_or_create_user(token_key, None, None)


class TokenAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        try:
            query_params = parse_qs(scope["query_string"].decode())
            scope["query_params"] = query_params
            token_key = query_params.get("Token")[0]
        except ValueError:
            token_key = None

        if settings.OIDC_ENABLED:
            user = await get_keycloak_user(token_key)
            scope["user"] = AnonymousUser() if user is None else user
        else:
            scope["user"] = (
                AnonymousUser() if token_key is None else await get_user(token_key)
            )

        return await super().__call__(scope, receive, send)
