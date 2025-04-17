from django_redis import get_redis_connection
from typing import Optional, Any


class CacheClient:
    def __init__(self) -> None:
        pass

    def get(self, key: str) -> Optional[Any]:
        with get_redis_connection() as redis_connection:
            return redis_connection.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        with get_redis_connection() as redis_connection:
            return redis_connection.set(key, value, ex=ex)

    def delete(self, key: str) -> bool:
        with get_redis_connection() as redis_connection:
            return redis_connection.delete(key)
