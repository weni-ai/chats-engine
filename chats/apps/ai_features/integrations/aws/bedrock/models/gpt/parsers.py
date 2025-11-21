import re


from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    ResponseBodyParser,
)


class GPTResponseBodyParser(ResponseBodyParser):
    """
    Parser for GPT response body.
    """

    REASONING_BLOCK_PATTERN = re.compile(
        r"<reasoning>.*?</reasoning>", flags=re.DOTALL | re.IGNORECASE
    )

    def parse(self, response_body: dict) -> str:
        """
        Parse the response body for the GPT client.
        Remove <reasoning>...</reasoning> blocks if present.
        """
        response_text = (
            response_body.get("choices")[0].get("message", {}).get("content", "")
        )

        # Remove reasoning block
        cleaned = re.sub(self.REASONING_BLOCK_PATTERN, "", response_text).strip()

        return cleaned
