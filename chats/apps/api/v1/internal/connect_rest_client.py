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
        request = requests.post(
            url=settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                "client_id": settings.OIDC_RP_CLIENT_ID,
                "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )
        token = request.json().get("access_token")
        return f"Bearer {token}"

    def create_ticketer(self, **kwargs):
        request = requests.post(
            url=f"{self.base_url}/v1/organization/project/create_ticketer/",
            headers=self.headers,
            params={**kwargs, "ticketer_type": "chats"},
        )
        return request.json()
