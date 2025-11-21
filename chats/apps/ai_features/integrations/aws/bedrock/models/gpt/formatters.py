from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
)


class GPTRequestBodyFormatter(RequestBodyFormatter):
    """
    Formatter for GPT request body.
    """

    def format(self, prompt_settings: dict, prompt: str) -> dict:
        """
        Format the request body for the GPT client.
        """
        return {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            **prompt_settings,
        }
