from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    ResponseBodyParser,
)


class NovaResponseBodyParser(ResponseBodyParser):
    """
    Parser for Nova response body.
    """

    def parse(self, response_body: dict) -> str:
        """
        Parse the response body for the Nova client.
        """
        return response_body.get("output").get("message").get("content")[0].get("text")
