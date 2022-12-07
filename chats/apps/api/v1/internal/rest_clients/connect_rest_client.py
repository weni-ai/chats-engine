import requests

from django.conf import settings
from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
    InternalAuthentication,
)


class ConnectRESTClient(InternalAuthentication):
    def __init__(self, *args, **kwargs):
        self.base_url = settings.CONNECT_API_URL

    def create_ticketer(self, **kwargs):
        response = requests.post(
            url=f"{self.base_url}/v1/organization/project/create_ticketer/",
            headers=self.headers,
            json={**kwargs, "ticketer_type": settings.FLOWS_TICKETER_TYPE},
        )
        return response

    def get_user_project_token(self, project, user_email: str):
        url = f"{self.base_url}/v1/organization/project/user_api_token/"
        params = {"user": user_email, "project_uuid": str(project.uuid)}
        response = requests.get(
            url=url,
            headers=self.headers,
            params=params,
        )

        return response
