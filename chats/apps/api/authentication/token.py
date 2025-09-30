import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone


class JWTTokenGenerator:
    """
    A class for generating JWT tokens with configurable options.

    This class provides methods to generate JWT tokens with custom payloads,
    expiration times, and signing algorithms.
    """

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        """
        Initialize the JWT token generator.

        Args:
            secret_key: The secret key for signing tokens. If None, uses Django's SECRET_KEY.
            algorithm: The signing algorithm to use (default: HS256).
        """
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm

    def generate_token(
        self,
        payload: Dict[str, Any],
        expires_in_hours: int = 24,
        issued_at: Optional[datetime] = None,
        not_before: Optional[datetime] = None,
    ) -> str:
        """
        Generate a JWT token with the specified payload and expiration time.

        Args:
            payload: Dictionary containing the token payload data.
            expires_in_hours: Token expiration time in hours (default: 24).
            issued_at: When the token was issued (default: current time).
            not_before: Token not valid before this time (default: current time).

        Returns:
            str: The encoded JWT token.

        Raises:
            jwt.InvalidTokenError: If token generation fails.
        """
        now = timezone.now()

        # Set default values
        if issued_at is None:
            issued_at = now
        if not_before is None:
            not_before = now

        # Calculate expiration time
        expires_at = issued_at + timedelta(hours=expires_in_hours)

        # Create token payload with standard claims
        token_payload = {
            **payload,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "nbf": int(not_before.timestamp()),
        }

        try:
            token = jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            raise jwt.InvalidTokenError(f"Failed to generate token: {str(e)}")

    def generate_api_token(
        self,
        service_name: str,
        permissions: Optional[list] = None,
        expires_in_hours: int = 168,  # 7 days for API tokens
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a JWT token for API service authentication.

        Args:
            service_name: Name of the service using the token.
            permissions: List of permissions granted to the service.
            expires_in_hours: Token expiration time in hours (default: 168).
            additional_claims: Additional claims to include in the token.

        Returns:
            str: The encoded JWT token.
        """
        payload = {
            "service": service_name,
            "type": "api_auth",
            "permissions": permissions or [],
        }

        if additional_claims:
            payload.update(additional_claims)

        return self.generate_token(payload, expires_in_hours)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token to verify.

        Returns:
            Dict[str, Any]: The decoded token payload.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is invalid.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
