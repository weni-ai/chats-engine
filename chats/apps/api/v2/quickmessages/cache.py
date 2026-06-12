from django.core.cache import cache


VERSION_KEY = "personal_qm_version"


def _get_version() -> int:
    version = cache.get(VERSION_KEY)
    if version is None:
        cache.set(VERSION_KEY, 1, timeout=None)
        return 1
    return version


def get_list_user_qm_cache_key(*, cursor: str, limit: str) -> str:
    version = _get_version()
    return f"personal_qm:v2:v{version}:{cursor}:{limit}"


def invalidate_personal_quick_messages_cache():
    version = cache.get(VERSION_KEY)
    cache.set(VERSION_KEY, (version or 0) + 1, timeout=None)
