import json
import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient


logger = logging.getLogger(__name__)


class BedrockClient(BaseAIPlatformClient):
    """
    Bedrock client for AWS Bedrock.
    """

    def __init__(self, model_id: str):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_BEDROCK_REGION_NAME,
        )
        self.model_id = model_id

    def get_text_from_response(self, response_body: dict) -> str:
        """
        Get the response text from the Bedrock client response body.
        Handles different response formats from different models:
        - Claude: response_body.get("content")[0].get("text")
        - Nova: response_body.get("output").get("message").get("content")[0].get("text")
        """
        # Try Claude format first
        if (
            "content" in response_body
            and len(response_body.get("content")) > 0
            and response_body.get("content")[0].get("text")
        ):
            return response_body.get("content")[0].get("text")

        # Try Nova format
        if (
            "output" in response_body
            and response_body.get("output").get("message").get("content")
            and len(response_body.get("output").get("message").get("content")) > 0
            and response_body.get("output").get("message").get("content")[0].get("text")
        ):
            return (
                response_body.get("output").get("message").get("content")[0].get("text")
            )

        # If neither format matches, raise an error
        raise ValueError(f"Unsupported response format: {response_body}")

    def format_request_body(self, prompt_settings: dict, prompt: str) -> dict:
        """
        Format the request body for the Bedrock client.
        """
        settings_body = {}

        for setting, value in prompt_settings.items():
            settings_body[setting] = value

        if "anthropic.claude" in self.model_id:
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
                **settings_body,
            }

        if "amazon.nova" in self.model_id:
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                **settings_body,
            }

        raise ValueError(f"Unsupported model: {self.model_id}")

    def generate_text(self, prompt_settings: dict, prompt: str) -> str:
        """
        Generate text using the Bedrock client.
        """
        try:
            request_body = self.format_request_body(prompt_settings, prompt)

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response.get("body").read().decode("utf-8"))

            return self.get_text_from_response(response_body)

        except (ClientError, Exception) as e:
            logger.error("ERROR: Can't invoke '%s'. Reason: %s", self.model_id, e)
            raise e
