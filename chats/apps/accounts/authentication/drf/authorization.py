import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header

from chats.apps.projects.models import ProjectPermission


class ProjectAdminDTO:
    def __init__(self, pk: str, project: str, user_email: str, role: int) -> None:
        self.pk = pk
        self.project = project
        self.user_email = user_email
        self.role = role

    def __dict__(self) -> dict:
        return {
            "pk": self.pk,
            "project": self.project,
            "user_email": self.user_email,
            "role": self.role,
        }


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

            return (authorization.user, authorization)
        except ProjectPermission.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

    def authenticate_credentials(self, key):
        if not self.cache_token:
            return super()._authenticate_credentials(key)
        redis_connection = get_redis_connection()

        cache_authorization = redis_connection.get(key)

        if cache_authorization is not None:
            cache_authorization = json.loads(cache_authorization)
            authorization = ProjectAdminDTO(**cache_authorization)
            return (authorization.user_email, authorization)

        auth_instance = super()._authenticate_credentials(key)[1]
        authorization = ProjectAdminDTO(
            pk=str(auth_instance.pk),
            project=str(auth_instance.project_id),
            user_email=auth_instance.user_id,
            role=auth_instance.role,
        )
        redis_connection.set(key, json.dumps(dict(authorization)), self.cache_ttl)

        return (authorization.user_email, authorization)
