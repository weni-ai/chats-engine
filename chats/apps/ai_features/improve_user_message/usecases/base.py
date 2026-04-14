from abc import ABC, abstractmethod


class BaseImproveUserMessageUsecase(ABC):
    """
    Base class for improve user message usecases.
    """

    feature_name: str

    @abstractmethod
    def execute(self, text: str) -> str:
        raise NotImplementedError
