import json
import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from chats.apps.ai_features.integrations.base_client import BaseClient


logger = logging.getLogger(__name__)


class BedrockClient(BaseClient):
    """
    Bedrock client for AWS Bedrock.
    """

    def __init__(self, model_id: str):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_BEDROCK_REGION_NAME,
        )
        self.model_id = model_id

    def generate_text(self, request_body: dict) -> str:
        """
        Generate text using the Bedrock client.
        """
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response.get("body").read().decode("utf-8"))

            return response_body.get("content")[0].get("text")

        except (ClientError, Exception) as e:
            logger.error("ERROR: Can't invoke '%s'. Reason: %s", self.model_id, e)
            raise e
