import json
from unittest.mock import MagicMock, patch
from django.test import TestCase

from chats.apps.ai_features.integrations.aws.bedrock.client import BedrockClient


class TestBedrockClient(TestCase):
    @patch("chats.apps.ai_features.integrations.aws.bedrock.client.boto3")
    def test_generate_text(self, mock_boto3):
        model_id = "anthropic.claude-v2:1"
        prompt = "What is the capital of Brazil?"
        mock_response_text = "The capital of Brazil is Brasília."

        mock_boto3.client.return_value = MagicMock()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"content": [{"text": mock_response_text}]}
        ).encode("utf-8")
        mock_boto3.client.return_value.invoke_model.return_value = {
            "body": mock_response
        }

        client = BedrockClient(model_id)

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.5,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }

        response = client.generate_text(request_body)

        self.assertEqual(response, mock_response_text)
