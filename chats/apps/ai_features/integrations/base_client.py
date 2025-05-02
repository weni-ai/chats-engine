from abc import ABC, abstractmethod


class BaseClient(ABC):
    """
    Base class for all AI clients.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id

    @abstractmethod
    def generate_text(self, request_body: dict) -> str:
        """
        Generate text using the AI client.
        """
