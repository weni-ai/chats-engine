from typing import Any, Dict, Tuple

from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import NexusRESTClient
from chats.core.cache_utils import (
    get_nexus_multi_agents_cached,
    set_nexus_multi_agents_cache,
)


class MultiAgentsNexusService:
    def __init__(self, client: NexusRESTClient = None):
        self.client = client or NexusRESTClient()

    def get_multi_agents(self, project_uuid: str) -> Tuple[Dict[str, Any], int]:
        cached = get_nexus_multi_agents_cached(project_uuid)
        if cached is not None:
            return cached, 200

        response = self.client.get_multi_agents(project_uuid)

        if response.status_code == 200:
            data = response.json()
            normalized = {"multi_agents": bool(data.get("multi_agents", False))}
            set_nexus_multi_agents_cache(project_uuid, normalized)
            return normalized, 200

        return self._extract_error_body(response), response.status_code

    @staticmethod
    def _extract_error_body(response) -> dict:
        try:
            return response.json()
        except Exception:
            return {"error": response.text}
