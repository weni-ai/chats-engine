from typing import List
from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
)
from chats.apps.ai_features.integrations.dataclass import PromptMessage


class GPTRequestBodyFormatter(RequestBodyFormatter):
    """
    Formatter for GPT request body.
    """

    def format(self, prompt_settings: dict, prompt_msgs: List[PromptMessage]) -> dict:
        """
        Format the request body for the GPT client.
        """
        return {
            "messages": [
                {
                    "role": "user",
                    "content": prompt_msg.text,
                }
                for prompt_msg in prompt_msgs
            ],
            **prompt_settings,
        }
