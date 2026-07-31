from django.conf import settings

from chats.apps.api.authentication.exceptions import InvalidTokenError
from chats.apps.api.authentication.services.jwt_service import JWTService
from chats.apps.api.authentication.token import CSATJWTTokenGenerator
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from chats.apps.projects.models.models import Project


class CSATJWTAuthentication(BaseAuthentication):
    """
    Authentication class for CSAT webhook JWT tokens.
    """

    def authenticate(self, request):
        """
        Authenticate the request using the JWT token.
        """
        token = request.headers.get("Authorization")

        if not token or not token.startswith("Token "):
            raise AuthenticationFailed("No authentication token provided.")

        try:
            token = token.split(" ")[1]
        except IndexError:
            raise AuthenticationFailed("Invalid authentication token.")

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        """
        Authenticate the credentials using the JWT token.
        """
        token_generator = CSATJWTTokenGenerator()
        try:
            payload = token_generator.verify_token(token)
            return (None, payload)
        except Exception as e:
            raise AuthenticationFailed(f"Invalid authentication token: {str(e)}")

    def authenticate_header(self, request):
        return "Token"


class InternalAPITokenAuthentication(BaseAuthentication):
    """
    Authentication class for the internal API token.
    """

    def authenticate(self, request):
        """
        Authenticate the request using the internal API token.
        """
        token = request.headers.get("Authorization")

        if not token or not token.startswith("Bearer "):
            return None

        try:
            token = token.split(" ")[1]
        except IndexError:
            return None

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        """
        Authenticate the credentials using the internal API token.
        """

        if token == "" or len(token) != len(settings.INTERNAL_API_TOKEN):
            return None

        if token != settings.INTERNAL_API_TOKEN:
            raise AuthenticationFailed("Invalid authentication token.")

        return (None, "INTERNAL")

    def authenticate_header(self, request):
        return "Bearer"


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization")

        if not header:
            return None

        try:
            header_parts = header.split(" ")
            if len(header_parts) != 2 or header_parts[0] != "Bearer":
                return None
        except Exception:
            return None

        token = header_parts[1]

        try:
            decoded_token = JWTService().decode_jwt_token(token)
        except InvalidTokenError:
            # Not a valid JWT (e.g. OIDC token); let other authenticators try
            return None

        project_uuid = decoded_token.get("project_uuid")

        if not project_uuid:
            raise AuthenticationFailed("Invalid token")

        request.project_uuid = project_uuid
        request.jwt_payload = decoded_token

        project = Project.objects.filter(uuid=project_uuid).first()

        if not project:
            raise AuthenticationFailed("Project not found")

        request.project = project

        return None, None

    def authenticate_header(self, request):
        return "Bearer"
