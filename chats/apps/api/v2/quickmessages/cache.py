from django.core.cache import cache


def _list_user_qm_version_key(user_id: int) -> str:
    return f"personal_qm_version:{user_id}"


def _get_list_user_qm_version(user_id: int) -> int:
    key = _list_user_qm_version_key(user_id)
    version = cache.get(key)
    if version is None:
        cache.set(key, 1, timeout=None)
        return 1
    return version


def get_list_user_qm_cache_key(*, user_id: int, cursor: str, limit: str) -> str:
    version = _get_list_user_qm_version(user_id)
    return f"personal_qm:v2:u{user_id}:v{version}:{cursor}:{limit}"


def invalidate_personal_quick_messages_cache(user_id: int):
    key = _list_user_qm_version_key(user_id)
    version = cache.get(key)
    cache.set(key, (version or 0) + 1, timeout=None)
