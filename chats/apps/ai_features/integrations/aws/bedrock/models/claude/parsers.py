from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    ResponseBodyParser,
)


class ClaudeResponseBodyParser(ResponseBodyParser):
    """
    Parser for Claude response body.
    """

    def parse(self, response_body: dict) -> str:
        """
        Parse the response body for the Claude client.
        """
        return response_body.get("content")[0].get("text")
