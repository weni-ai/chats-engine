import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from chats.apps.ai_features.integrations.aws.bedrock.client import BedrockClient


class TestBedrockClientExtra(TestCase):
    @override_settings(AWS_BEDROCK_REGION_NAME="us-east-1")
    @patch("chats.apps.ai_features.integrations.aws.bedrock.client.boto3")
    def test_generate_text_nova_format(self, mock_boto3):
        model_id = "amazon.nova-pro-v1"
        prompt = "Say hi"
        mock_boto3.client.return_value = MagicMock()
        body = {"output": {"message": {"content": [{"text": "Hi!"}]}}}
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(body).encode("utf-8")
        mock_boto3.client.return_value.invoke_model.return_value = {"body": mock_body}
        client = BedrockClient(model_id)
        resp = client.generate_text({"temperature": 0.1}, prompt)
        self.assertEqual(resp, "Hi!")

    def test_get_text_from_response_unsupported_raises(self):
        client = BedrockClient.__new__(BedrockClient)
        with self.assertRaises(ValueError):
            client.get_text_from_response({"unexpected": "format"})

    def test_format_request_body_unsupported_model_raises(self):
        client = BedrockClient.__new__(BedrockClient)
        client.model_id = "other.model"
        with self.assertRaises(ValueError):
            client.format_request_body({}, "p")

