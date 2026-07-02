from django.core.cache import cache


SECTOR_VERSION_KEY = "sector_qm_version:{sector_uuid}"
PROJECT_VERSION_KEY = "project_qm_version:{project_uuid}"


def _get_version(key: str) -> int:
    version = cache.get(key)
    if version is None:
        cache.set(key, 1, timeout=None)
        return 1
    return version


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


def get_list_cache_key(
    *, sector_uuid: str = None, project_uuid: str = None, cursor: str, limit: str
) -> str:
    if sector_uuid:
        version_key = SECTOR_VERSION_KEY.format(sector_uuid=sector_uuid)
        version = _get_version(version_key)
        return f"sector_qm:v2:sector:{sector_uuid}:v{version}:{cursor}:{limit}"

    version_key = PROJECT_VERSION_KEY.format(project_uuid=project_uuid)
    version = _get_version(version_key)
    return f"sector_qm:v2:project:{project_uuid}:v{version}:{cursor}:{limit}"


def invalidate_sector_quick_messages_cache(sector_uuid: str, project_uuid: str):
    sector_key = SECTOR_VERSION_KEY.format(sector_uuid=sector_uuid)
    project_key = PROJECT_VERSION_KEY.format(project_uuid=project_uuid)

    sector_version = cache.get(sector_key)
    project_version = cache.get(project_key)

    cache.set(sector_key, (sector_version or 0) + 1, timeout=None)
    cache.set(project_key, (project_version or 0) + 1, timeout=None)
