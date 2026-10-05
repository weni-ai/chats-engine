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

        logger.exception(
            "Internal error on %s %s: %s",
            request.method,
            request.get_full_path(),
            exception,
        )

        response_data = {
            "code": "INTERNAL_ERROR",
            "message": "An internal error has occurred",
            "event_id": event_id or "unknown",
        }

        if settings.DEBUG:
            response_data["detail"] = traceback.format_exc()

        return JsonResponse(response_data, status=500)


class ElasticAPMTraceResponseHeaderMiddleware:
    """
    Expose Elastic APM distributed-tracing identifiers as response headers so
    the values are visible in the browser DevTools (Network tab) and readable
    by frontend instrumentation that needs to correlate a request with its
    trace in Kibana.

    The upstream ``elasticapm`` Python agent only writes trace headers on
    outgoing HTTP calls; for incoming requests it just reads them. This
    middleware fills that gap by writing ``traceparent`` (W3C),
    ``tracestate`` (W3C, when present) and the legacy
    ``elastic-apm-traceparent`` header on every response that ran inside an
    active APM transaction.

    Must be placed *after* ``elasticapm.contrib.django.middleware.TracingMiddleware``
    in ``MIDDLEWARE`` so the transaction already exists by the time the
    response is built.
    """

    LEGACY_HEADER_NAME = "elastic-apm-traceparent"
    TRACEPARENT_HEADER_NAME = "traceparent"
    TRACESTATE_HEADER_NAME = "tracestate"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._inject_trace_headers(response)
        return response

    def _inject_trace_headers(self, response):
        try:
            import elasticapm
        except ImportError:
            return

        try:
            transaction = elasticapm.get_transaction()
        except Exception:
            logger.debug("Failed to read active Elastic APM transaction", exc_info=True)
            return

        trace_parent = getattr(transaction, "trace_parent", None) if transaction else None
        if not trace_parent:
            return

        try:
            traceparent_value = trace_parent.to_string()
        except Exception:
            logger.debug("Failed to serialize Elastic APM trace parent", exc_info=True)
            return

        response[self.TRACEPARENT_HEADER_NAME] = traceparent_value
        response[self.LEGACY_HEADER_NAME] = traceparent_value

        tracestate = getattr(trace_parent, "tracestate", None)
        if tracestate:
            response[self.TRACESTATE_HEADER_NAME] = tracestate
