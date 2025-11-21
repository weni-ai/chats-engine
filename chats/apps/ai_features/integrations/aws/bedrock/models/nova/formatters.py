from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
)


class NovaRequestBodyFormatter(RequestBodyFormatter):
    """
    Formatter for Nova request body.
    """

    def format(self, prompt_settings: dict, prompt: str) -> dict:
        """
        Format the request body for the Nova client.
        """
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            **prompt_settings,
        }
