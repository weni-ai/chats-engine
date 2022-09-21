import requests
from django.conf import settings


class FlowRESTClient:
    def __init__(self):
        self.base_url = settings.FLOWS_API_URL
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

    def create_queue(self, uuid: str, name: str, sector_uuid: str):
        request = requests.post(
            url=f"{self.base_url}/api/v2/internals/{sector_uuid}/queues/",
            headers=self.headers,
            params={"uuid": uuid, "name": name},
        )
        return request.json()

    def update_queue(self, uuid: str, name: str, sector_uuid: str):
        request = requests.patch(
            url=f"{self.base_url}/api/v2/internals/{sector_uuid}/queues/{uuid}/",
            headers=self.headers,
            params={"name": name},
        )
        return request.json()

    def destroy_queue(self, uuid: str, sector_uuid: str):
        request = requests.delete(
            url=f"{self.base_url}/api/v2/internals/{sector_uuid}/queues/{uuid}/",
            headers=self.headers,
        )
        return request.json()
