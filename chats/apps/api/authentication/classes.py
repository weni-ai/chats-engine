from chats.apps.api.authentication.token import JWTTokenGenerator
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTAuthentication(BaseAuthentication):
    """
    Authentication class for the JWT token.
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
        token_generator = JWTTokenGenerator()
        try:
            payload = token_generator.verify_token(token)
            return (None, payload)
        except Exception as e:
            raise AuthenticationFailed(f"Invalid authentication token: {str(e)}")

    def authenticate_header(self, request):
        return "Token"
