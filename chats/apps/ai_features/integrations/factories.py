from typing import Type, Dict
from chats.apps.ai_features.integrations.aws.bedrock.client import BedrockClient
from chats.apps.ai_features.integrations.base_client import BaseAIPlatformClient


CLIENTS_MAPPING: Dict[str, Type[BaseAIPlatformClient]] = {
    "bedrock": BedrockClient,
}


class AIModelPlatformClientFactory:
    """
    Factory for creating AI clients.
    """

    @staticmethod
    def get_client_class(client_name: str) -> Type[BaseAIPlatformClient]:
        """
        Get the client class for the given client name.
        """
        try:
            return CLIENTS_MAPPING[client_name]
        except KeyError as e:
            raise ValueError(f"Invalid client name: {client_name}") from e
