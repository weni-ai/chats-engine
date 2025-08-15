from django.conf import settings
from django_redis import get_redis_connection
from django.contrib.auth import get_user_model
from typing import Optional

User = get_user_model()

EMAIL_LOOKUP_TTL = getattr(settings, "EMAIL_LOOKUP_TTL", 300)
EMAIL_LOOKUP_NEG_TTL = getattr(settings, "EMAIL_LOOKUP_NEG_TTL", 60)
EMAIL_LOOKUP_CACHE_ENABLED = getattr(settings, "EMAIL_LOOKUP_CACHE_ENABLED", True)

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