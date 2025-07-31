from typing import Any, Optional
from chats.core.cache import BaseCacheClient


class MockCacheClient(BaseCacheClient):
    def get(self, key: str) -> Optional[Any]:
        return None

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        return True

    def delete(self, key: str) -> bool:
        return True
