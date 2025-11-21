from django.test import TestCase

from chats.apps.ai_features.integrations.aws.bedrock.models.claude.formatters import (
    ClaudeRequestBodyFormatter,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.claude.parsers import (
    ClaudeResponseBodyParser,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.gpt.formatters import (
    GPTRequestBodyFormatter,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.gpt.parsers import (
    GPTResponseBodyParser,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.nova.formatters import (
    NovaRequestBodyFormatter,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.nova.parsers import (
    NovaResponseBodyParser,
)
from chats.apps.ai_features.integrations.aws.bedrock.models.registries import (
    ModelRequestBodyFormatterRegistry,
    ModelResponseBodyParserRegistry,
)


class TestModelRequestBodyFormatterRegistry(TestCase):
    def test_get_formatter_claude(self):
        registry = ModelRequestBodyFormatterRegistry()
        formatter = registry.get_formatter("anthropic.claude-v2:1")
        self.assertIsInstance(formatter, ClaudeRequestBodyFormatter)

    def test_get_formatter_nova(self):
        registry = ModelRequestBodyFormatterRegistry()
        formatter = registry.get_formatter("amazon.nova:1")
        self.assertIsInstance(formatter, NovaRequestBodyFormatter)

    def test_get_formatter_gpt(self):
        registry = ModelRequestBodyFormatterRegistry()
        formatter = registry.get_formatter("amazon.gpt:1")
        self.assertIsInstance(formatter, GPTRequestBodyFormatter)

    def test_get_formatter_invalid(self):
        registry = ModelRequestBodyFormatterRegistry()
        with self.assertRaises(ValueError):
            registry.get_formatter("invalid.model:1")


class TestModelResponseBodyParserRegistry(TestCase):
    def test_get_parser_claude(self):
        registry = ModelResponseBodyParserRegistry()
        parser = registry.get_parser("anthropic.claude-v2:1")
        self.assertIsInstance(parser, ClaudeResponseBodyParser)

    def test_get_parser_nova(self):
        registry = ModelResponseBodyParserRegistry()
        parser = registry.get_parser("amazon.nova:1")
        self.assertIsInstance(parser, NovaResponseBodyParser)

    def test_get_parser_gpt(self):
        registry = ModelResponseBodyParserRegistry()
        parser = registry.get_parser("amazon.gpt:1")
        self.assertIsInstance(parser, GPTResponseBodyParser)

    def test_get_parser_invalid(self):
        registry = ModelResponseBodyParserRegistry()
        with self.assertRaises(ValueError):
            registry.get_parser("invalid.model:1")
