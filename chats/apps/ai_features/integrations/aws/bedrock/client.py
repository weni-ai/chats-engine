import json
import logging
from typing import List

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from chats.apps.ai_features.integrations.aws.bedrock.models.registries import (
    ModelRequestBodyFormatterRegistry,
    ModelResponseBodyParserRegistry,
)
from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient
from chats.apps.ai_features.integrations.dataclass import PromptMessage


logger = logging.getLogger(__name__)


class BedrockClient(BaseAIPlatformClient):
    """
    Bedrock client for AWS Bedrock.
    """

    def __init__(
        self,
        model_id: str,
        request_body_formatter_registry: ModelRequestBodyFormatterRegistry = ModelRequestBodyFormatterRegistry(),
        response_body_parser_registry: ModelResponseBodyParserRegistry = ModelResponseBodyParserRegistry(),
    ):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_BEDROCK_REGION_NAME,
        )
        self.model_id = model_id
        self.request_body_formatter_registry = request_body_formatter_registry
        self.response_body_parser_registry = response_body_parser_registry

    def get_text_from_response(self, response_body: dict) -> str:
        """
        Get the response text from the Bedrock client response body.
        Handles different response formats from different models.
        """
        parser = self.response_body_parser_registry.get_parser(self.model_id)

        return parser.parse(response_body)

    def format_request_body(self, prompt_settings: dict, prompt: str) -> dict:
        """
        Format the request body for the Bedrock client.
        """
        formatter = self.request_body_formatter_registry.get_formatter(self.model_id)

        return formatter.format(prompt_settings, prompt)

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
