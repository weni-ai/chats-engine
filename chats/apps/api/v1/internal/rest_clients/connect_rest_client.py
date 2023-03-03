import requests

from django.conf import settings
from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
    InternalAuthentication,
)


class ConnectRESTClient(InternalAuthentication):
    def __init__(self, *args, **kwargs):
        self.base_url = settings.CONNECT_API_URL

    def create_ticketer(self, **kwargs):
        url = f"{self.base_url}/v1/organization/project/create_ticketer/"
        if settings.USE_CONNECT_V2:
            project_uuid = kwargs.pop("project_uuid")
            url = f"{self.base_url}/v2/projects/{project_uuid}/ticketer"
        response = requests.post(
            url=url,
            headers=self.headers,
            json={**kwargs, "ticketer_type": settings.FLOWS_TICKETER_TYPE},
        )
        return response

    def get_user_project_token(self, project, user_email: str):
        params = {"user": user_email}
        project_uuid = str(project.uuid)
        if settings.USE_CONNECT_V2:
            url = f"{self.base_url}/v2/projects/{project_uuid}/user-api-token"
        else:
            url = f"{self.base_url}/v1/organization/project/user_api_token/"
            params["project_uuid"] = project_uuid

        response = requests.get(
            url=url,
            headers=self.headers,
            params=params,
        )

        return response
