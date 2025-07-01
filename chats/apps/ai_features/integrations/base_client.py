from abc import ABC, abstractmethod


class BaseAIPlatformClient(ABC):
    """
    Base class for all AI model platform clients.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id

    @abstractmethod
    def generate_text(self, prompt_settings: dict, prompt: str) -> str:
        """
        Generate text using the AI model platform client.
        """
