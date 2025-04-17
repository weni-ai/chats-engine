import json
from uuid import UUID

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from mozilla_django_oidc.contrib.drf import OIDCAuthentication

from chats.apps.projects.models import ProjectPermission


TOKEN_AUTHENTICATION_CLASS = (
    OIDCAuthentication if settings.OIDC_ENABLED else TokenAuthentication
)


class ProjectAdminDTO:
    def __init__(
        self, pk: str, project: str, user_email: str, user_first_name: str, role: int
    ) -> None:
        self.pk = pk
        self.project = project
        self.user_email = user_email
        self.user_first_name = user_first_name
        self.role = role


class ProjectAdminAuthentication(TokenAuthentication):
    keyword = "Bearer"
    model = ProjectPermission

    cache_token = settings.OIDC_CACHE_TOKEN
    cache_ttl = settings.OIDC_CACHE_TTL

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _(
                "Invalid token header. Token string should not contain invalid characters."
            )
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def _authenticate_credentials(self, key):
        model = self.get_model()
        try:
            authorization = model.auth.get(uuid=key)
            if not authorization.is_admin:
                raise exceptions.PermissionDenied()
            authorization = ProjectAdminDTO(
                pk=str(authorization.pk),
                project=str(authorization.project_id),
                user_email=authorization.user_id or "",
                user_first_name=(
                    authorization.user.first_name if authorization.user else ""
                ),
                role=authorization.role,
            )
            return (authorization.user_email, authorization)
        except ProjectPermission.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

    def authenticate_credentials(self, key):
        if not self.cache_token:
            return self._authenticate_credentials(key)
        redis_connection = get_redis_connection()

        cache_authorization = redis_connection.get(key)

        if cache_authorization is not None:
            cache_authorization = json.loads(cache_authorization)
            authorization = ProjectAdminDTO(**cache_authorization)
            return (authorization.user_email, authorization)

        authorization = self._authenticate_credentials(key)[1]
        redis_connection.set(key, json.dumps(authorization.__dict__), self.cache_ttl)

        return (authorization.user_email, authorization)


def get_auth_class(request):
    auth = get_authorization_header(request)
    token = auth.split()[1].decode() if len(auth.split()) > 1 else ""

    try:
        UUID(token)
        return [ProjectAdminAuthentication]
    except ValueError:
        return [TOKEN_AUTHENTICATION_CLASS]
