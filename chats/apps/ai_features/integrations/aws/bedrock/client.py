import json

import boto3
from botocore.exceptions import ClientError

from chats.apps.ai_features.integrations.base_client import BaseClient


class BedrockClient(BaseClient):
    """
    Bedrock client for AWS Bedrock.
    """

    def __init__(self, model_id: str):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",  # TODO: make this configurable, use env variable
        )
        self.model_id = model_id

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using the Bedrock client.
        """
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({"prompt": prompt}),
            )

            return response.get("body").read().decode("utf-8")
        except (ClientError, Exception) as e:
            print(f"ERROR: Can't invoke '{self.model_id}'. Reason: {e}")
            exit(1)
