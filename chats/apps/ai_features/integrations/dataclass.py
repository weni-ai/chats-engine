from dataclasses import dataclass


@dataclass(frozen=True)
class PromptMessage:
    """
    Message to be sent to the AI model.
    """

    text: str
    should_cache: bool = False
