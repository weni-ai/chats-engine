import base64

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from standardwebhooks import Webhook

import logging

logger = logging.getLogger(__name__)


class GrowthbookSignatureAuthentication(BaseAuthentication):
    """
    Authentication for the Growthbook webhook.
    """

    def authenticate(self, request):
        """
        Authenticate the Growthbook webhook using
        the signature provided in the request headers.
        """
        secret = settings.GROWTHBOOK_WEBHOOK_SECRET

        raw = request.body
        headers = {k.lower(): v for k, v in request.headers.items()}

        # https://docs.growthbook.io/app/webhooks/sdk-webhooks#standard-webhooks
        try:
            wh = Webhook(base64.b64encode(secret.encode()).decode())
            wh.verify(raw, headers)
        except Exception as e:
            logger.error("Signature verification failed: %s", e)
            raise AuthenticationFailed("Signature verification failed") from e

        return (None, None)

    def authenticate_header(self, request):
        """
        Return a string to be used as the WWW-Authenticate header in a
        401 Unauthorized response, or None if the authentication scheme
        should return 403 Forbidden responses.
        """
        return "Growthbook-Signature"
