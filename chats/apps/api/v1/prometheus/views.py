import os

from django.http import HttpResponse, HttpResponseForbidden
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def metrics_view(request):
    auth_token = request.headers.get("Authorization")
    prometheus_auth_token = os.environ.get("PROMETHEUS_AUTH_TOKEN")

    expected_token = f"Bearer {prometheus_auth_token}"
    if not auth_token or auth_token != expected_token:
        return HttpResponseForbidden("Access denied")

    from prometheus_client import REGISTRY

    return HttpResponse(generate_latest(REGISTRY), content_type=CONTENT_TYPE_LATEST)
