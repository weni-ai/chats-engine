import json
import logging
from typing import Callable, TYPE_CHECKING

import requests
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import status

from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
    InternalAuthentication,
)
from chats.core.requests import get_request_session_with_retries


if TYPE_CHECKING:
    from chats.apps.projects.models.models import Project


LOGGER = logging.getLogger(__name__)


def get_cursor(url):
    cursor = url.split("cursor=")[-1]
    return cursor


def check_flows_labels(labels: list) -> bool:
    """
    Check if there is a label named like 'settings.CHATS_FLOWS_TAG' in the given list
    """
    for label in labels:
        if settings.CHATS_FLOWS_TAG == label["name"]:
            return True
    return False


def retry_request_and_refresh_flows_auth_token(
    project,
    request_method: Callable,
    headers: dict,
    url: str,
    params: dict = None,
    json=None,
    user_email: str = "",
    retries: int = settings.FLOWS_AUTH_TOKEN_RETRIES,
):
    permissions = list(project.admin_permissions.values_list("user__email", flat=True))
    for _ in range(0, retries):
        response = request_method(url=url, params=params, json=json, headers=headers)
        if response.status_code in [401, 403]:
            token = project.set_flows_project_auth_token(
                user_email=user_email, permissions=permissions
            )
            headers["Authorization"] = f"Token {token}"
        else:
            break
    return response


class FlowsQueueMixin:
    def create_queue(self, uuid: str, name: str, sector_uuid: str, project_uuid: str):
        response = requests.post(
            url=f"{self.base_url}/api/v2/internals/ticketers/{sector_uuid}/queues/",
            headers=self.headers,
            json={"uuid": uuid, "name": name, "project_uuid": project_uuid},
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to create the queue.  response: {response.content}"
            )
        return response

    def update_queue(self, uuid: str, name: str, sector_uuid: str):
        response = requests.patch(
            url=f"{self.base_url}/api/v2/internals/ticketers/{sector_uuid}/queues/{uuid}/",
            headers=self.headers,
            json={"name": name},
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to update the queue. response: {response.content}"
            )
        return response

    def destroy_queue(self, uuid: str, sector_uuid: str, project_uuid: str):
        response = requests.delete(
            url=f"{self.base_url}/api/v2/internals/ticketers/{sector_uuid}/queues/{uuid}/",
            json={"project_uuid": project_uuid},
            headers=self.headers,
        )

        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to delete the queue. response: {response.content}"
            )
        return response


class FlowsContactsAndGroupsMixin:
    def project_headers(self, token):
        headers = {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": f"Token {token}",
        }
        return headers

    def list_contacts(self, project, cursor: str = "", query_filters: dict = {}):
        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.get,
            headers=self.project_headers(project.flows_authorization),
            params=query_filters,
            url=f"{self.base_url}/api/v2/contacts.json?cursor={cursor}",
        )
        contacts = response.json()
        contacts["next"] = get_cursor(contacts.get("next") or "")
        contacts["previous"] = get_cursor(contacts.get("previous") or "")
        return contacts

    def validate_contact_exists(self, urn, project):
        number = urn.split(":")[1]
        num_variations = [f"{number[:4]}{number[-8:]}", f"{number[:4]}9{number[-8:]}"]
        for num_var in num_variations:
            response = self.list_contacts(
                project=project, query_filters={"urn": f"whatsapp:{num_var}"}
            )
            if response.get("results") != []:
                return True  # contact already exists, early return
        return False  # contact does not exist

    def create_contact(self, project, data: dict, contact_id: str = ""):
        url = (
            f"{self.base_url}/api/v2/contacts.json"
            if contact_id == ""
            else f"{self.base_url}/api/v2/contacts.json?uuid={contact_id}"
        )
        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.post,
            url=url,
            json=data,
            headers=self.project_headers(project.flows_authorization),
        )
        return response

    def list_contact_groups(self, project, cursor: str = "", query_filters: dict = {}):
        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.get,
            headers=self.project_headers(project.flows_authorization),
            params=query_filters,
            url=f"{self.base_url}/api/v2/groups.json?cursor={cursor}",
        )
        groups = response.json()
        groups["next"] = get_cursor(groups.get("next") or "")
        groups["previous"] = get_cursor(groups.get("previous") or "")
        return groups


class FlowsSectorMixin:
    def create_ticketer(self, project_uuid: str, name: str, config: dict):
        url = f"{self.base_url}/api/v2/internals/ticketers/"
        body = {
            "project": project_uuid,
            "ticketer_type": settings.FLOWS_TICKETER_TYPE,
            "name": name,
            "config": config,
        }

        response = requests.post(url=url, headers=self.headers, json=body, timeout=120)
        return response

    def destroy_sector(
        self,
        sector_uuid: str,
        user_email: str,
    ):
        response = requests.delete(
            url=f"{self.base_url}/api/v2/internals/sectors/{sector_uuid}/?user={user_email}/",
            headers=self.headers,
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to delete the sector. response: {response.content}"
            )
        return response


class FlowRESTClient(
    InternalAuthentication,
    FlowsContactsAndGroupsMixin,
    FlowsQueueMixin,
    FlowsSectorMixin,
):
    def __init__(self, *args, **kwargs):
        self.base_url = settings.FLOWS_API_URL

    def get_user_api_token(self, project_uuid: str, user_email: str):
        params = dict(project=project_uuid, user=user_email)
        response = requests.get(
            url=f"{self.base_url}/api/v2/internals/users/api-token",
            params=params,
            headers=self.headers,
        )
        return response

    def list_flows(self, project, cursor: str = ""):
        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.get,
            headers=self.project_headers(project.flows_authorization),
            url=f"{self.base_url}/api/v2/flows.json?cursor={cursor}",
        )
        flows = response.json()
        flows["next"] = get_cursor(flows.get("next") or "")
        flows["previous"] = get_cursor(flows.get("previous") or "")
        results = flows["results"]
        flows["results"] = [
            flow
            for flow in results
            if flow["labels"] != [] and check_flows_labels(flow["labels"])
        ]
        return flows

    def retrieve_flow_definitions(self, project, flow_uuid):
        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.get,
            headers=self.project_headers(project.flows_authorization),
            url=f"{self.base_url}/api/v2/definitions.json?flow={flow_uuid}",
        )
        flows = response.json()
        return flows

    def start_flow(self, project, data):
        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.post,
            url=f"{self.base_url}/api/v2/flow_starts.json",
            json=data,
            headers=self.project_headers(project.flows_authorization),
        )
        return response.json()

    def update_ticket_assignee(self, ticket_uuid: str, user_email: str):
        url = f"{self.base_url}/api/v2/internals/ticket_assignee"

        data = {
            "uuid": ticket_uuid,
            "email": user_email,
        }

        request_session = get_request_session_with_retries(
            status_forcelist=[429, 500, 502, 503, 504], method_whitelist=["POST"]
        )

        request_session.post(
            url,
            data=json.dumps(
                data,
                sort_keys=True,
                indent=1,
                cls=DjangoJSONEncoder,
            ),
            headers=self.headers,
        )

    def create_flow_or_update_flow(self, project: "Project", definition: dict):
        payload = {
            "project_uuid": str(project.uuid),
            "definition": definition,
        }

        response = retry_request_and_refresh_flows_auth_token(
            project=project,
            request_method=requests.post,
            url=f"{self.base_url}/api/v2/definitions.json",
            json=json.dumps(payload, sort_keys=True, indent=1, cls=DjangoJSONEncoder),
            headers=self.headers,
        )
        return response.json()
