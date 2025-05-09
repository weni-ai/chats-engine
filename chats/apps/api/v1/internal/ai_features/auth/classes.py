import hmac

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


def verify_signature(secret: str, signature: str, body):
    """
    Verify the signature of the request.
    """

    # Run HMAC-SHA256 on the request body using the configured signing secret
    valid_signature = hmac.new(
        bytes(secret, "utf-8"), bytes(body, "utf-8"), "sha256"
    ).hexdigest()

    # use constant time string comparison to prevent timing attacks
    return hmac.compare_digest(valid_signature, signature)


class AIFeaturesAuthentication(BaseAuthentication):
    """
    Authentication class for the AI Features API.
    """

    def authenticate(self, request):
        signature_header_name = "X-Weni-Signature"

        signature = request.headers.get(signature_header_name)

        if not signature:
            raise AuthenticationFailed("No signature found")

        if not verify_signature(
            settings.AI_FEATURES_PROMPTS_API_SECRET,
            signature,
            request.body,
        ):
            raise AuthenticationFailed("Invalid signature")
