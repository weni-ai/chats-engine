import logging
import traceback
import sentry_sdk

from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class InternalErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        event_id = sentry_sdk.last_event_id()

        if not event_id:
            event_id = sentry_sdk.capture_exception(exception)

        logger.exception(f"Internal error: {exception}")

        response_data = {
            "code": "INTERNAL_ERROR",
            "message": "An internal error has occurred",
            "event_id": event_id or "unknown",
        }

        if settings.DEBUG:
            response_data["detail"] = traceback.format_exc()

        return JsonResponse(response_data, status=500)
