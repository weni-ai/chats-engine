import requests
from django.conf import settings


class OpenAIClient:
    BASE_URL = settings.OPEN_AI_BASE_URL

    def headers(self, token):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    def chat_completion(self, token, messages):
        url = f"{self.BASE_URL}chat/completions"
        response = requests.post(
            url=url,
            headers=self.headers(token),
            json={
                "model": settings.OPEN_AI_GPT_VERSION,
                "messages": messages,
            },
        )
        return response
