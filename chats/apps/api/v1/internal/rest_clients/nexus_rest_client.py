import logging

import requests
from django.conf import settings

from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
    InternalAuthentication,
)
from chats.core.requests import get_request_session_with_retries

logger = logging.getLogger(__name__)


class NexusRESTClient(InternalAuthentication):
    def __init__(self):
        self.base_url = settings.NEXUS_API_URL.rstrip("/")

    def _get_session(self):
        return get_request_session_with_retries(
            retries=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["GET", "PATCH"],
        )

    def get_human_support(self, project_uuid: str) -> requests.Response:
        url = f"{self.base_url}/api/{project_uuid}/human-support"
        session = self._get_session()
        response = session.get(url=url, headers=self.headers, timeout=10)
        return response

    def patch_human_support(
        self, project_uuid: str, data: dict
    ) -> requests.Response:
        url = f"{self.base_url}/api/{project_uuid}/human-support"
        session = self._get_session()
        response = session.patch(url=url, headers=self.headers, json=data, timeout=10)
        return response
