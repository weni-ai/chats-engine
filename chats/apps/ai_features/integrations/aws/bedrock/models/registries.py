from typing import Dict

from chats.apps.ai_features.integrations.aws.bedrock.models.base import (
    RequestBodyFormatter,
    ResponseBodyParser,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.claude.formatters import (
    ClaudeRequestBodyFormatter,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.claude.parsers import (
    ClaudeResponseBodyParser,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.nova.formatters import (
    NovaRequestBodyFormatter,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.nova.parsers import (
    NovaResponseBodyParser,
)


class ModelRequestBodyFormatterRegistry:
    """
    Registry for model formatters.
    """

    _formatters: Dict[str, RequestBodyFormatter] = {
        "anthropic.claude": ClaudeRequestBodyFormatter,
        "amazon.nova": NovaRequestBodyFormatter,
    }

    @classmethod
    def get_formatter(cls, model_id: str) -> RequestBodyFormatter:
        """Get the appropriate formatter for a model ID."""
        for prefix, formatter in cls._formatters.items():
            if prefix in model_id:
                return formatter
        raise ValueError(f"Unsupported model: {model_id}")


class ModelResponseBodyParserRegistry:
    """
    Registry for model response body parsers.
    """

    _parsers: Dict[str, ResponseBodyParser] = {
        "anthropic.claude": ClaudeResponseBodyParser,
        "amazon.nova": NovaResponseBodyParser,
    }

    @classmethod
    def get_parser(cls, model_id: str) -> ResponseBodyParser:
        """Get the appropriate parser for a model ID."""
        for prefix, parser in cls._parsers.items():
            if prefix in model_id:
                return parser
        raise ValueError(f"Unsupported model: {model_id}")
