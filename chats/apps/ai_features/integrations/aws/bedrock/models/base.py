from abc import ABC, abstractmethod
from typing import List

from chats.apps.ai_features.integrations.dataclass import PromptMessage


class RequestBodyFormatter(ABC):
    """
    Abstract class for request body formatters.
    """

    @abstractmethod
    def format(self, prompt_settings: dict, prompt_msgs: List[PromptMessage]) -> dict:
        """
        Format the request body for the AI model platform client.
        """
        raise NotImplementedError


class ResponseBodyParser(ABC):
    """
    Abstract class for response body parsers.
    """

    @abstractmethod
    def parse(self, response_body: dict) -> str:
        """
        Parse the response body for the AI model platform client.
        """
        raise NotImplementedError
