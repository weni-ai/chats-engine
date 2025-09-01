from django.conf import settings

from chats.apps.feature_flags.integrations.growthbook.clients import GrowthbookClient
from chats.core.cache import CacheClient


GROWTHBOOK_CLIENT = GrowthbookClient(
    host_base_url=settings.GROWTHBOOK_HOST_BASE_URL,
    client_key=settings.GROWTHBOOK_CLIENT_KEY,
    cache_client=CacheClient(),
    short_cache_key=settings.GROWTHBOOK_SHORT_CACHE_KEY,
    short_cache_ttl=settings.GROWTHBOOK_SHORT_CACHE_TTL,
    long_cache_key=settings.GROWTHBOOK_LONG_CACHE_KEY,
    long_cache_ttl=settings.GROWTHBOOK_LONG_CACHE_TTL,
    is_singleton=True,
)
