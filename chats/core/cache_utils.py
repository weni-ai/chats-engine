import json
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
try:
	from django_redis import get_redis_connection as _get_redis_connection  # type: ignore
except Exception:
	_get_redis_connection = None  # type: ignore

def get_redis_connection():
	if _get_redis_connection is None:
		raise RuntimeError("django_redis is not installed or not configured")
	return _get_redis_connection()

User = get_user_model()

EMAIL_LOOKUP_TTL = getattr(settings, "EMAIL_LOOKUP_TTL", 300)
EMAIL_LOOKUP_NEG_TTL = getattr(settings, "EMAIL_LOOKUP_NEG_TTL", 60)
EMAIL_LOOKUP_CACHE_ENABLED = getattr(settings, "EMAIL_LOOKUP_CACHE_ENABLED", True)
PROJECT_LOOKUP_TTL = getattr(settings, "PROJECT_LOOKUP_TTL", 600)
PROJECT_CONFIG_TTL = getattr(settings, "PROJECT_CONFIG_TTL", 900)
PROJECT_CACHE_ENABLED = getattr(settings, "PROJECT_CACHE_ENABLED", True)


def get_user_id_by_email_cached(email: str) -> Optional[int]:
    if not EMAIL_LOOKUP_CACHE_ENABLED:
        try:
            return User.objects.only("id").get(email=(email or "").lower()).pk
        except User.DoesNotExist:
            return None
    email = (email or "").lower()
    if not email:
        return None
    try:
        r = get_redis_connection()
    except Exception:
        r = None

    k = f"user:email:{email}"
    if r:
        v = r.get(k)
        if v:
            if v == b"-1":
                return None
            uid = int(v)
            try:
                if User.objects.filter(pk=uid).exists():
                    return uid
                else:
                    r.delete(k)
            except Exception:
                pass
    try:
        uid = User.objects.only("id").get(email=email).pk
        if r:
            r.setex(k, EMAIL_LOOKUP_TTL, uid)
        return uid
    except User.DoesNotExist:
        if r:
            r.setex(k, EMAIL_LOOKUP_NEG_TTL, -1)  # negative cache
        return None


def invalidate_user_email_cache(email: str) -> None:
    """
    Invalidate the cache for a specific email
    """
    if not EMAIL_LOOKUP_CACHE_ENABLED:
        return

    email = (email or "").lower()
    if not email:
        return

    try:
        r = get_redis_connection()
        k = f"user:email:{email}"
        r.delete(k)
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
        r = get_redis_connection()
    except Exception:
        r = None
    
    k = f"project:uuid:{uuid}"
    if r:
        v = r.get(k)
        if v:
            if v == b"-1":
                return None
            return json.loads(v)
    
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
        if r:
            r.setex(k, PROJECT_LOOKUP_TTL, json.dumps(project_data))
        return project_data
    except Project.DoesNotExist:
        if r:
            r.setex(k, PROJECT_LOOKUP_TTL, -1)  # negative cache
        return None


def get_project_config_cached(project_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get project config by UUID from cache.
    """
    if not PROJECT_CACHE_ENABLED:
        try:
            from chats.apps.projects.models import Project
            config = Project.objects.get(uuid=project_uuid).config or {}
            return dict(config)
        except Project.DoesNotExist:
            return None
    
    try:
        r = get_redis_connection()
    except Exception:
        r = None
    
    k = f"project:config:{project_uuid}"
    if r:
        v = r.get(k)
        if v:
            return json.loads(v) if v != b"-1" else None
    
    # Get from database
    try:
        from chats.apps.projects.models import Project
        config = Project.objects.get(uuid=project_uuid).config or {}
        if r:
            r.setex(k, PROJECT_CONFIG_TTL, json.dumps(config))
        return dict(config)
    except Project.DoesNotExist:
        if r:
            r.setex(k, PROJECT_CONFIG_TTL, -1)
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
        r = get_redis_connection()
        # Delete all project-related keys
        r.delete(f"project:uuid:{project_uuid}")
        r.delete(f"project:config:{project_uuid}")
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