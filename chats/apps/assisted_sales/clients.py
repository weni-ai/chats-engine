import logging

import requests
from django.conf import settings

from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
    InternalAuthentication,
)
from chats.apps.assisted_sales.exceptions import CopilotConnectError

logger = logging.getLogger(__name__)


class CopilotConnectClient(InternalAuthentication):
    def create_copilot_project(self, name: str, project_uuid: str) -> dict:
        url = settings.CONNECT_COPILOT_CREATE_URL
        if not url:
            raise CopilotConnectError(
                status_code=502,
                error="Connect copilot create URL is not configured",
            )

        try:
            response = requests.post(
                url=url,
                headers=self.headers,
                json={"name": name, "project_uuid": project_uuid},
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to create copilot project on Connect")
            raise CopilotConnectError(status_code=502, error=str(exc)) from exc

        if not response.ok:
            raise CopilotConnectError(
                status_code=response.status_code,
                error=self._parse_error(response),
            )

        return self._parse_json(response)

    def switch_copilot_project(
        self, old_copilot_uuid: str, new_copilot_uuid: str
    ) -> dict:
        url = settings.CONNECT_COPILOT_UPDATE_URL
        if not url:
            raise CopilotConnectError(
                status_code=502,
                error="Connect copilot update URL is not configured",
            )

        request_url = url.format(uuid=old_copilot_uuid)
        try:
            response = requests.put(
                url=request_url,
                headers=self.headers,
                json={"new_uuid": new_copilot_uuid},
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to switch copilot project on Connect")
            raise CopilotConnectError(status_code=502, error=str(exc)) from exc

        if not response.ok:
            raise CopilotConnectError(
                status_code=response.status_code,
                error=self._parse_error(response),
            )

        return self._parse_json(response)

    def get_assigned_agents(self, copilot_project_uuid: str) -> int:
        url = settings.CONNECT_COPILOT_AGENTS_COUNT_URL
        if not url:
            return 0

        request_url = url.format(uuid=copilot_project_uuid)
        params = {}
        if "{uuid}" not in url:
            params["project_uuid"] = copilot_project_uuid

        try:
            response = requests.get(
                url=request_url,
                headers=self.headers,
                params=params or None,
                timeout=15,
            )
        except requests.RequestException:
            logger.exception(
                "Failed to fetch assigned agents for copilot %s",
                copilot_project_uuid,
            )
            return 0

        if not response.ok:
            logger.warning(
                "Assigned agents endpoint returned %s for copilot %s",
                response.status_code,
                copilot_project_uuid,
            )
            return 0

        data = self._parse_json(response)
        return int(data.get("assigned_agents", data.get("count", 0)) or 0)

    def _parse_json(self, response) -> dict:
        try:
            data = response.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def _parse_error(self, response):
        data = self._parse_json(response)
        if data.get("error") not in (None, {}):
            return data.get("error")
        return response.text or "Connect request failed"
