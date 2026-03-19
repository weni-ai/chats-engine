import logging
from typing import Any, Dict, Tuple

from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import NexusRESTClient
from chats.core.cache_utils import get_nexus_settings_cached, set_nexus_settings_cache

logger = logging.getLogger(__name__)


class HumanSupportNexusService:
    def __init__(self, client: NexusRESTClient = None):
        self.client = client or NexusRESTClient()

    def get_settings(self, project_uuid: str) -> Tuple[Dict[str, Any], int]:
        cached = get_nexus_settings_cached(project_uuid)
        if cached is not None:
            return cached, 200

        response = self.client.get_human_support(project_uuid)

        if response.status_code == 200:
            data = response.json()
            set_nexus_settings_cache(project_uuid, data)
            return data, 200

        return self._extract_error_body(response), response.status_code

    def update_settings(
        self, project_uuid: str, data: dict
    ) -> Tuple[Dict[str, Any], int]:
        response = self.client.patch_human_support(project_uuid, data)

        if response.status_code == 200:
            response_data = response.json()
            set_nexus_settings_cache(project_uuid, response_data)
            return response_data, 200

        return self._extract_error_body(response), response.status_code

    @staticmethod
    def _extract_error_body(response) -> dict:
        try:
            return response.json()
        except Exception:
            return {"error": response.text}
