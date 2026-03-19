import logging

import requests
from django.conf import settings

from chats.core.requests import get_request_session_with_retries

logger = logging.getLogger(__name__)


class NexusRESTClient:
    def __init__(self, auth_token: str):
        self.base_url = settings.NEXUS_API_URL.rstrip("/")
        self.auth_token = auth_token

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": self.auth_token,
        }

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
