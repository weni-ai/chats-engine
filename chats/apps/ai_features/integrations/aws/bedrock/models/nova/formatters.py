from typing import List
from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
)
from chats.apps.ai_features.integrations.dataclass import PromptMessage


class NovaRequestBodyFormatter(RequestBodyFormatter):
    """
    Formatter for Nova request body.
    """

    def format(self, prompt_settings: dict, prompt_msgs: List[PromptMessage]) -> dict:
        """
        Format the request body for the Nova client.
        """
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt_msg.text,
                            **(
                                {"cachePoint": {"type": "default"}}
                                if prompt_msg.should_cache
                                else {}
                            ),
                        }
                    ],
                }
                for prompt_msg in prompt_msgs
            ],
            **prompt_settings,
        }
