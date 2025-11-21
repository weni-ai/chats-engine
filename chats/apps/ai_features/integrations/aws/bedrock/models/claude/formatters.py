from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
)


class ClaudeRequestBodyFormatter(RequestBodyFormatter):
    """
    Formatter for Claude request body.
    """

    def format(self, prompt_settings: dict, prompt: str) -> dict:
        """
        Format the request body for the Claude client.
        """
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            **prompt_settings,
        }
