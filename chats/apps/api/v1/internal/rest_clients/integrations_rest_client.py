import requests
from django.conf import settings

from chats.core.views import search_dict_list


class IntegrationsRESTClient:
    def __init__(self, *args, **kwargs):
        self.base_url = settings.INTEGRATIONS_API_URL

    def chatgpt_headers(self, token: str) -> dict:
        headers = {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": token,
        }
        return headers

    def get_chatgpt_token(self, project_uuid: str, token: str):
        response = requests.get(
            url=f"{self.base_url}/api/v1/my-apps/?configured=true&project_uuid={project_uuid}",
            headers=self.chatgpt_headers(token),
        )
        try:
            app_list = response.json()
            chat_gpt_app = search_dict_list(app_list, "code", "chatgpt")
            return chat_gpt_app.get("config").get("api_key")
        except AttributeError:
            return None
