from typing import List
from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
)
from chats.apps.ai_features.integrations.dataclass import PromptMessage


class ClaudeRequestBodyFormatter(RequestBodyFormatter):
    """
    Formatter for Claude request body.
    """

    def format(self, prompt_settings: dict, prompt_msgs: List[PromptMessage]) -> dict:
        """
        Format the request body for the Claude client.
        """
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_msg.text,
                            **(
                                {"cache_control": {"type": "ephemeral"}}
                                if prompt_msg.should_cache
                                else {}
                            ),
                        },
                    ],
                }
                for prompt_msg in prompt_msgs
            ],
            **prompt_settings,
        }
