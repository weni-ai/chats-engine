from django_redis import get_redis_connection
from typing import List, Optional, Any


class CacheClient:
    def __init__(self) -> None:
        pass

    def get(self, key: str) -> Optional[Any]:
        with get_redis_connection() as redis_connection:
            return redis_connection.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        with get_redis_connection() as redis_connection:
            return redis_connection.set(key, value, ex=ex)

    def get_list(self, pattern: str) -> List[str]:
        with get_redis_connection() as redis_connection:
            keys = []
            cursor = 0
            while True:
                cursor, partial_keys = redis_connection.scan(
                    cursor=cursor, match=pattern
                )
                keys.extend(partial_keys)
                if cursor == 0:
                    break
            return keys

    def delete(self, key: str) -> bool:
        with get_redis_connection() as redis_connection:
            return redis_connection.delete(key)
