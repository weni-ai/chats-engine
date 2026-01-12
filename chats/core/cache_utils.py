import json
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection

User = get_user_model()

EMAIL_LOOKUP_TTL = getattr(settings, "EMAIL_LOOKUP_TTL", 300)
EMAIL_LOOKUP_NEG_TTL = getattr(settings, "EMAIL_LOOKUP_NEG_TTL", 60)
EMAIL_LOOKUP_CACHE_ENABLED = getattr(settings, "EMAIL_LOOKUP_CACHE_ENABLED", True)
PROJECT_LOOKUP_TTL = getattr(settings, "PROJECT_LOOKUP_TTL", 600)
PROJECT_CONFIG_TTL = getattr(settings, "PROJECT_CONFIG_TTL", 900)
PROJECT_CACHE_ENABLED = getattr(settings, "PROJECT_CACHE_ENABLED", True)
USER_OBJECT_CACHE_TTL = getattr(settings, "USER_OBJECT_CACHE_TTL", 300)
USER_OBJECT_CACHE_ENABLED = getattr(settings, "USER_OBJECT_CACHE_ENABLED", True)


def _normalize_email(email: Optional[str]) -> Optional[str]:
    """
    Normalize email string for consistent cache and DB lookups.
    """
    if not email:
        return None
    return email.strip().lower()


def _get_redis_connection_safe():
    try:
        return get_redis_connection()
    except Exception:
        return None


def _get_user_id_from_db(email: str) -> Optional[int]:
    try:
        return User.objects.only("id").get(email=email).pk
    except User.DoesNotExist:
        return None


def _validate_cached_user_id(user_id: int, redis_conn, cache_key: str) -> Optional[int]:
    try:
        if User.objects.filter(pk=user_id).exists():
            return user_id
        redis_conn.delete(cache_key)
    except Exception:
        pass
    return None


def _check_cache_for_user_id(redis_conn, cache_key: str) -> Optional[int]:
    if not redis_conn:
        return None
    cached_value = redis_conn.get(cache_key)
    if not cached_value:
        return None
    if cached_value == b"-1":
        return -1  # negative cache marker
    user_id = int(cached_value)
    return _validate_cached_user_id(user_id, redis_conn, cache_key)


def get_user_id_by_email_cached(email: str) -> Optional[int]:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None

    if not EMAIL_LOOKUP_CACHE_ENABLED:
        return _get_user_id_from_db(normalized_email)

    redis_conn = _get_redis_connection_safe()
    cache_key = f"user:email:{normalized_email}"

    cached_result = _check_cache_for_user_id(redis_conn, cache_key)
    if cached_result == -1:
        return None
    if cached_result is not None:
        return cached_result

    user_id = _get_user_id_from_db(normalized_email)
    if redis_conn:
        if user_id:
            redis_conn.setex(cache_key, EMAIL_LOOKUP_TTL, user_id)
        else:
            redis_conn.setex(cache_key, EMAIL_LOOKUP_NEG_TTL, -1)
    return user_id


def invalidate_user_email_cache(email: str) -> None:
    """
    Invalidate the cache for a specific email
    """
    if not EMAIL_LOOKUP_CACHE_ENABLED:
        return

    normalized_email = _normalize_email(email)
    if not normalized_email:
        return

    try:
        redis_conn = get_redis_connection()
        cache_key = f"user:email:{normalized_email}"
        redis_conn.delete(cache_key)
    except Exception:
        # If Redis is down, we can't invalidate, but that's ok
        # because the fallback will query the database anyway
        pass


def invalidate_user_cache_by_id(user_id: int) -> None:
    """
    Invalidate cache for a user by their ID.
    Useful when we don't know the old email.
    """
    if not EMAIL_LOOKUP_CACHE_ENABLED:
        return

    try:
        user = User.objects.only("email").get(pk=user_id)
        invalidate_user_email_cache(user.email)
    except User.DoesNotExist:
        pass


def get_project_by_uuid_cached(uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get project data by UUID from cache or database.
    Returns a dict with essential project fields.
    """
    if not PROJECT_CACHE_ENABLED:
        try:
            from chats.apps.projects.models import Project

            project = Project.objects.get(uuid=uuid)
            return {
                "uuid": str(project.uuid),
                "name": project.name,
                "timezone": str(project.timezone),
                "date_format": project.date_format,
                "org": project.org,
                "is_template": project.is_template,
                "room_routing_type": project.room_routing_type,
            }
        except Project.DoesNotExist:
            return None

    if not uuid:
        return None

    try:
        redis_conn = get_redis_connection()
    except Exception:
        redis_conn = None

    cache_key = f"project:uuid:{uuid}"
    if redis_conn:
        cached_value = redis_conn.get(cache_key)
        if cached_value:
            if cached_value == b"-1":
                return None
            return json.loads(cached_value)

    # Get from database
    try:
        from chats.apps.projects.models import Project

        project = Project.objects.get(uuid=uuid)
        project_data = {
            "uuid": str(project.uuid),
            "name": project.name,
            "timezone": str(project.timezone),
            "date_format": project.date_format,
            "org": project.org,
            "is_template": project.is_template,
            "room_routing_type": project.room_routing_type,
        }
        if redis_conn:
            redis_conn.setex(cache_key, PROJECT_LOOKUP_TTL, json.dumps(project_data))
        return project_data
    except Project.DoesNotExist:
        if redis_conn:
            redis_conn.setex(cache_key, PROJECT_LOOKUP_TTL, -1)  # negative cache
        return None


def get_project_config_cached(project_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get project config by UUID from cache.
    """
    if not PROJECT_CACHE_ENABLED:
        try:
            from chats.apps.projects.models import Project

            config = Project.objects.get(uuid=project_uuid).config or {}
            return {**config}
        except Project.DoesNotExist:
            return None

    try:
        redis_conn = get_redis_connection()
    except Exception:
        redis_conn = None

    cache_key = f"project:config:{project_uuid}"
    if redis_conn:
        cached_value = redis_conn.get(cache_key)
        if cached_value:
            return json.loads(cached_value) if cached_value != b"-1" else None

    # Get from database
    try:
        from chats.apps.projects.models import Project

        config = Project.objects.get(uuid=project_uuid).config or {}
        if redis_conn:
            redis_conn.setex(cache_key, PROJECT_CONFIG_TTL, json.dumps(config))
        return {**config}
    except Project.DoesNotExist:
        if redis_conn:
            redis_conn.setex(cache_key, PROJECT_CONFIG_TTL, -1)
        return None


def invalidate_project_cache(project_uuid: str) -> None:
    """
    Invalidate all caches for a specific project
    """
    if not PROJECT_CACHE_ENABLED:
        return

    if not project_uuid:
        return

    try:
        redis_conn = get_redis_connection()
        # Delete all project-related keys
        redis_conn.delete(f"project:uuid:{project_uuid}")
        redis_conn.delete(f"project:config:{project_uuid}")
    except Exception:
        pass


def invalidate_project_cache_by_id(project_id: int) -> None:
    """
    Invalidate cache for a project by its ID
    """
    if not PROJECT_CACHE_ENABLED:
        return

    try:
        from chats.apps.projects.models import Project

        project = Project.objects.only("uuid").get(pk=project_id)
        invalidate_project_cache(str(project.uuid))
    except Project.DoesNotExist:
        pass


def _get_user_from_db(email: str) -> Optional[User]:
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None


def _build_user_from_cache(user_data: dict) -> User:
    user = User(
        id=user_data["id"],
        email=user_data["email"],
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        is_staff=user_data["is_staff"],
        is_active=user_data["is_active"],
        is_superuser=user_data["is_superuser"],
        language=user_data.get("language"),
        photo_url=user_data.get("photo_url"),
    )
    user._state.adding = False
    return user


def _serialize_user_for_cache(user: User) -> str:
    user_data = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "language": user.language,
        "photo_url": user.photo_url,
    }
    return json.dumps(user_data)


def _get_user_from_cache(redis_conn, cache_key: str) -> Optional[User]:
    if not redis_conn:
        return None
    cached_value = redis_conn.get(cache_key)
    if not cached_value:
        return None
    if cached_value == b"-1":
        return -1  # negative cache marker
    try:
        user_data = json.loads(cached_value)
        return _build_user_from_cache(user_data)
    except (json.JSONDecodeError, KeyError):
        redis_conn.delete(cache_key)
        return None


def get_cached_user(email: str) -> Optional[User]:
    """
    Get full User object by email from cache or database.
    Caches the entire user object to avoid database queries.

    Args:
        email: User email address

    Returns:
        User object if found, None if not found
    """
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None

    if not USER_OBJECT_CACHE_ENABLED:
        print(
            f"[CACHE] User object cache DISABLED - querying DB for: {normalized_email}"
        )
        return _get_user_from_db(normalized_email)

    redis_conn = _get_redis_connection_safe()
    if not redis_conn:
        print(f"[CACHE ERROR] Failed to connect to Redis for email: {normalized_email}")

    cache_key = f"user:object:{normalized_email}"

    cached_user = _get_user_from_cache(redis_conn, cache_key)
    if cached_user == -1:
        print(f"[CACHE HIT] Negative cache for user object: {normalized_email}")
        return None
    if cached_user is not None:
        print(
            f"[CACHE HIT] Found user object id={cached_user.id} for email: {normalized_email}"
        )
        return cached_user

    user = _get_user_from_db(normalized_email)
    if user:
        print(
            f"[CACHE MISS] Queried DB and found user id={user.id} for email: {normalized_email}"
        )
        if redis_conn:
            redis_conn.setex(
                cache_key, USER_OBJECT_CACHE_TTL, _serialize_user_for_cache(user)
            )
            print(
                f"[CACHE CREATE] Cached user object with TTL={USER_OBJECT_CACHE_TTL}s"
            )
    else:
        print(f"[CACHE MISS] User object not found in DB for email: {normalized_email}")
        if redis_conn:
            redis_conn.setex(cache_key, EMAIL_LOOKUP_NEG_TTL, -1)
            print(
                f"[CACHE CREATE] Created negative cache with TTL={EMAIL_LOOKUP_NEG_TTL}s"
            )

    return user


def invalidate_cached_user(email: str) -> None:
    """
    Invalidate the cached user object for a specific email.
    Also invalidates the email lookup cache.
    Args:
        email: User email address to invalidate
    """
    if not USER_OBJECT_CACHE_ENABLED:
        return

    normalized_email = _normalize_email(email)
    if not normalized_email:
        return

    try:
        redis_conn = get_redis_connection()
        cache_key = f"user:object:{normalized_email}"
        redis_conn.delete(cache_key)
        invalidate_user_email_cache(email)
    except Exception:
        pass
