import hmac
import time

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS


def verify_signature(secret: str, signature: str, message):
    """
    Verify the signature of the request.
    """

    # Run HMAC-SHA256 on the message using the configured signing secret
    valid_signature = hmac.new(
        bytes(secret, "utf-8"), bytes(message, "utf-8"), "sha256"
    ).hexdigest()

    # use constant time string comparison to prevent timing attacks
    return hmac.compare_digest(valid_signature, signature)


def verify_timestamp(timestamp: str):
    """
    Verify the timestamp of the request.
    """

    # Check if the timestamp is within the last 5 minutes
    if abs(time.time() - float(timestamp)) > 300:
        raise AuthenticationFailed("Timestamp is too old")


class AIFeaturesAuthentication(BaseAuthentication):
    """
    Authentication class for the AI Features API.
    """

    def authenticate(self, request):
        signature_header_name = "X-Weni-Signature"
        timestamp_header_name = "X-Timestamp"

        signature = request.headers.get(signature_header_name)

        if not signature:
            raise AuthenticationFailed("No signature found")

        timestamp = request.headers.get(timestamp_header_name)

        if not timestamp:
            raise AuthenticationFailed("No timestamp found")

        verify_timestamp(timestamp)

        if request.method in SAFE_METHODS:
            message = str(timestamp)
        else:
            message = f"{request.body}+{timestamp}"

        message = f"{request.body}+{timestamp}"

        if not verify_signature(
            settings.AI_FEATURES_PROMPTS_API_SECRET,
            signature,
            message,
        ):
            raise AuthenticationFailed("Invalid signature")

        verify_timestamp(timestamp)
