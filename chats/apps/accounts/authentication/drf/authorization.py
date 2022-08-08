from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import (TokenAuthentication,
                                           get_authorization_header)
from chats.apps.projects.models import ProjectPermission


class ProjectAuthentication(TokenAuthentication):
    keyword = "Bearer"
    model = ProjectPermission

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

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            authorization = model.objects.get(uuid=key)
            if not authorization.can_translate:
                raise exceptions.PermissionDenied()

            return (authorization.user, authorization)
        except ProjectPermission.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))
