import requests

from django.conf import settings


class ConnectRESTClient:
    def __init__(self):
        self.base_url = settings.CONNECT_API_URL
        self.headers = {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.get_auth_token(),
        }

    def get_auth_token(self) -> str:
        if settings.OIDC_ENABLED:

            request = requests.post(
                url=settings.OIDC_OP_TOKEN_ENDPOINT,
                data={
                    "client_id": settings.OIDC_RP_CLIENT_ID,
                    "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                    "grant_type": "client_credentials",
                },
            )
            token = request.json().get("access_token")
        else:
            token = ""
        return f"Bearer {token}"

    def create_ticketer(self, **kwargs):
        response = requests.post(
            url=f"{self.base_url}/v1/organization/project/create_ticketer/",
            headers=self.headers,
            json={**kwargs, "ticketer_type": settings.FLOWS_TICKETER_TYPE},
        )
        return response

    def get_user_project_token(self, project, user_email):
        url = (f"{self.base_url}/v1/organization/project/{project.pk}/user_api_token/",)
        params = {"user": user_email, "project_uuid": str(project.uuid)}
        response = requests.get(
            url=url,
            headers=self.headers,
            params=params,
        )

        return response
