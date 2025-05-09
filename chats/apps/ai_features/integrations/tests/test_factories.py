from django.test import TestCase

from chats.apps.ai_features.integrations.aws.bedrock.client import BedrockClient
from chats.apps.ai_features.integrations.factories import AIModelPlatformClientFactory


class TestAIModelPlatformClientFactory(TestCase):
    def test_get_bedrock_client_class(self):
        client_class = AIModelPlatformClientFactory.get_client_class("bedrock")
        self.assertEqual(client_class, BedrockClient)

    def test_get_invalid_client_class(self):
        invalid_client_name = "invalid"

        with self.assertRaises(ValueError) as context:
            AIModelPlatformClientFactory.get_client_class(invalid_client_name)

        self.assertEqual(
            str(context.exception), f"Invalid client name: {invalid_client_name}"
        )
