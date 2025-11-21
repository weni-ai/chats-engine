from abc import ABC, abstractmethod


class RequestBodyFormatter(ABC):
    """
    Abstract class for request body formatters.
    """

    @abstractmethod
    def format(self, prompt_settings: dict, prompt: str) -> dict:
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
