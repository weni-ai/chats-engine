import requests


class OpenAIClient:
    BASE_URL = "https://api.openai.com/v1/"

    def headers(self, token):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    def chat_completion(self, token, messages):
        url = f"{self.BASE_URL}chat/completions"
        response = requests.post(
            url=url,
            headers=self.headers(token),
            json={"model": "gpt-3.5-turbo", "messages": messages},
        )
        return response
