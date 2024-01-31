from abc import ABC, abstractmethod
from typing import List

from .dto import Filters, RoomData


class RoomsDataRepository(ABC):
    @abstractmethod
    def get_cache_key(self, filters: Filters) -> str:
        pass

    @abstractmethod
    def get_rooms_data(self, filters: Filters) -> List["RoomData"]:
        pass


class CacheRepository(ABC):
    @abstractmethod
    def get(self, key: str, default=None):
        """Obtém dados do cache com base na chave."""
        pass

    @abstractmethod
    def set(self, key: str, data):
        """Define dados no cache com uma chave associada."""
        pass
