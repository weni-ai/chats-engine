import logging

import requests
from django.conf import settings

from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
    InternalAuthentication,
)
from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import NexusRESTClient
from chats.apps.assisted_sales.exceptions import CopilotConnectError

logger = logging.getLogger(__name__)

COPILOT_REQUEST_TIMEOUT_SECONDS = 15
FLOWS_REQUEST_TIMEOUT_SECONDS = 15
HTTP_502_BAD_GATEWAY = 502
HTTP_UNAUTHORIZED = 401


class CopilotConnectClient(InternalAuthentication):
    def _copilot_create_url(self, organization_uuid: str) -> str:
        base_url = (settings.CONNECT_API_URL or "").rstrip("/")
        if base_url:
            return f"{base_url}/v2/organizations/{organization_uuid}/projects/"

        template = settings.CONNECT_COPILOT_CREATE_URL
        if template:
            return template.format(
                org_uuid=organization_uuid,
                organization_uuid=organization_uuid,
                uuid=organization_uuid,
            )

        raise CopilotConnectError(
            status_code=HTTP_502_BAD_GATEWAY,
            error="Connect API URL is not configured",
        )

    def _user_headers(self, authorization: str) -> dict:
        if not authorization or not str(authorization).strip():
            raise CopilotConnectError(
                status_code=HTTP_UNAUTHORIZED,
                error="User authorization is required to create a copilot project",
            )
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": str(authorization).strip(),
        }

    def create_copilot_project(
        self,
        *,
        name: str,
        parent_project_uuid: str,
        organization_uuid: str,
        timezone: str,
        date_format: str = None,
        authorization: str,
    ) -> dict:
        url = self._copilot_create_url(organization_uuid)

        payload = {
            "name": name,
            "timezone": timezone,
            "is_live_desk_copilot": True,
            "parent_project_uuid": parent_project_uuid,
        }
        if date_format:
            payload["date_format"] = date_format

        try:
            response = requests.post(
                url=url,
                headers=self._user_headers(authorization),
                json=payload,
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

    def remove_copilot_project(self, copilot_project_uuid: str) -> None:
        url = settings.CONNECT_COPILOT_REMOVE_URL
        if not url:
            return

        request_url = url.format(uuid=copilot_project_uuid)
        try:
            response = requests.delete(
                url=request_url,
                headers=self.headers,
                timeout=COPILOT_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to remove copilot project on Connect")
            raise CopilotConnectError(status_code=502, error=str(exc)) from exc

        if not response.ok:
            raise CopilotConnectError(
                status_code=response.status_code,
                error=self._parse_error(response),
            )

    def get_assigned_agents(self, copilot_project_uuid: str) -> int:
        if not settings.NEXUS_API_URL:
            return 0

        try:
            response = NexusRESTClient().get_projects_agents(copilot_project_uuid)
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
        if not isinstance(data, dict):
            return 0

        target = str(copilot_project_uuid).lower()
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("project_uuid") or "").lower() != target:
                continue
            custom = int(item.get("custom_agents_count") or 0)
            official = int(item.get("official_agents_count") or 0)
            return custom + official
        return 0

    def get_project_authorization(self, project_uuid: str, user_email: str) -> dict:
        base_url = (settings.CONNECT_API_URL or "").rstrip("/")
        if not base_url:
            raise CopilotConnectError(
                status_code=502,
                error="Connect API URL is not configured",
            )

        url = f"{base_url}/v2/projects/{project_uuid}/authorization"
        try:
            response = requests.get(
                url=url,
                headers=self.headers,
                params={"user": user_email},
                timeout=COPILOT_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to fetch project authorization on Connect")
            raise CopilotConnectError(status_code=502, error=str(exc)) from exc

        if not response.ok:
            raise CopilotConnectError(
                status_code=response.status_code,
                error=self._parse_error(response),
            )

        data = self._parse_json(response)
        return data if isinstance(data, dict) else {}

    def list_copilot_projects(
        self, org_uuid: str, name: str = None, authorization: str = None
    ) -> list:
        request_url, headers = self._copilot_list_request(org_uuid, authorization)
        if not request_url:
            return None

        items = self._fetch_connect_project_pages(request_url, headers)
        copilots = [item for item in items if self._is_live_desk_copilot(item)]
        if name:
            needle = str(name).strip().lower()
            copilots = [
                item
                for item in copilots
                if needle in str(item.get("name") or "").lower()
            ]
        return copilots

    def _copilot_list_request(self, org_uuid: str, authorization: str):
        try:
            url = self._copilot_create_url(org_uuid)
        except CopilotConnectError:
            template = settings.CONNECT_COPILOT_LIST_URL
            if not template:
                return None, None
            return (
                template.format(org_uuid=org_uuid, uuid=org_uuid),
                self.headers,
            )
        return url, self._user_headers(authorization)

    def _fetch_connect_project_pages(self, request_url: str, headers: dict) -> list:
        items = []
        next_url = request_url
        while next_url:
            try:
                response = requests.get(
                    url=next_url,
                    headers=headers,
                    timeout=COPILOT_REQUEST_TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                logger.exception("Failed to list copilot projects on Connect")
                raise CopilotConnectError(status_code=502, error=str(exc)) from exc

            if not response.ok:
                raise CopilotConnectError(
                    status_code=response.status_code,
                    error=self._parse_error(response),
                )

            page_items, next_url = self._parse_project_list_page(
                self._parse_json(response)
            )
            items.extend(page_items)
        return items

    def _parse_project_list_page(self, data):
        if isinstance(data, list):
            return data, None
        if isinstance(data, dict):
            page_items = (
                data.get("results") or data.get("projects") or data.get("data") or []
            )
            if not isinstance(page_items, list):
                page_items = []
            return page_items, data.get("next") or None
        return [], None

    def _is_live_desk_copilot(self, item: dict) -> bool:
        if not isinstance(item, dict):
            return False
        flag = item.get("is_live_desk_copilot")
        if flag is True:
            return True
        if isinstance(flag, str):
            return flag.strip().lower() in ("true", "1")
        return False

    def list_internal_messages(
        self,
        *,
        project_uuid: str,
        contact_urn: str,
        cursor: str = None,
        limit: int = None,
    ) -> dict:
        base_url = (settings.FLOWS_API_URL or "").rstrip("/")
        if not base_url:
            raise CopilotConnectError(
                status_code=502,
                error="Flows API URL is not configured",
            )

        params = {
            "project_uuid": project_uuid,
            "contact_urn": contact_urn,
        }
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = limit

        url = f"{base_url}/api/v2/internals/messages"
        try:
            response = requests.get(
                url=url,
                headers=self.headers,
                params=params,
                timeout=FLOWS_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to list copilot messages on Flows")
            raise CopilotConnectError(status_code=502, error=str(exc)) from exc

        if not response.ok:
            raise CopilotConnectError(
                status_code=response.status_code,
                error=self._parse_error(response),
            )

        data = self._parse_json(response)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"next": None, "previous": None, "results": data}
        return {"next": None, "previous": None, "results": []}

    def _parse_json(self, response):
        try:
            data = response.json()
        except ValueError:
            return {}
        return data

    def _parse_error(self, response):
        data = self._parse_json(response)
        if isinstance(data, dict) and data.get("error") not in (None, {}):
            return data.get("error")
        return response.text or "Connect request failed"
