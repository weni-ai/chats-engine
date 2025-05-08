import hmac

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


def verify_signature(signature_header_name: str, secret: str, headers: dict, body):
    """
    Verify the signature of the request.
    """

    if signature_header_name not in headers:
        return False

    # get the v1 signature from the header
    signature_from_header = {
        k: v
        for k, v in [
            pair.split("=") for pair in headers[signature_header_name].split(",")
        ]
    }["v1"]

    # Run HMAC-SHA256 on the request body using the configured signing secret
    valid_signature = hmac.new(
        bytes(secret, "utf-8"), bytes(body, "utf-8"), "sha256"
    ).hexdigest()

    # use constant time string comparison to prevent timing attacks
    return hmac.compare_digest(valid_signature, signature_from_header)


class AIFeaturesAuthentication(BaseAuthentication):
    """
    Authentication class for the AI Features API.
    """

    def authenticate(self, request):
        signature_header_name = "X-Weni-Signature"

        if not verify_signature(
            signature_header_name,
            settings.AI_FEATURES_PROMPTS_API_SECRET,
            request.headers,
            request.body,
        ):
            raise AuthenticationFailed("Invalid signature")
