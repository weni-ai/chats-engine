from abc import ABC, abstractmethod
import threading
import requests
import logging
from sentry_sdk import capture_exception

from chats.core.cache import CacheClient


logger = logging.getLogger(__name__)


class BaseGrowthbookClient(ABC):
    """
    Base class for Growthbook client.
    """

    @abstractmethod
    def get_feature_flags_from_short_cache(self) -> dict:
        """
        Get feature flags from short cache
        """
        raise NotImplementedError

    @abstractmethod
    def get_feature_flags_from_long_cache(self) -> dict:
        """
        Get feature flags from long cache
        """
        raise NotImplementedError

    @abstractmethod
    def get_feature_flags_from_cache(self) -> None:
        """
        Get feature flags from cache
        """
        raise NotImplementedError

    @abstractmethod
    def set_feature_flags_to_short_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to short cache
        """
        raise NotImplementedError

    @abstractmethod
    def set_feature_flags_to_long_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to long cache
        """
        raise NotImplementedError

    @abstractmethod
    def set_feature_flags_to_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to cache
        """
        raise NotImplementedError

    @abstractmethod
    def update_feature_flags_definitions(self) -> None:
        """
        Update feature flags definitions from Growthbook's API.
        """
        raise NotImplementedError

    @abstractmethod
    def get_feature_flags(self) -> dict:
        """
        Get feature flags.
        """
        raise NotImplementedError


class GrowthbookClient(BaseGrowthbookClient):
    _instance = None
    _lock = threading.Lock()

    def __new__(
        cls,
        host_base_url: str,
        api_key: str,
        cache_client: CacheClient,
        short_cache_ttl: int,
        long_cache_ttl: int,
    ):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.host_base_url = host_base_url
                cls._instance.api_key = api_key
                cls._instance.cache_client = cache_client
                cls._instance.short_cache_ttl = short_cache_ttl
                cls._instance.long_cache_ttl = long_cache_ttl
                cls._instance._last_local_update = None
        return cls._instance

    def __init__(
        self,
        host_base_url: str,
        api_key: str,
        cache_client: CacheClient,
        short_cache_ttl: int,
        long_cache_ttl: int,
    ):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.host_base_url = host_base_url
            self.api_key = api_key
            self.cache_client: CacheClient = cache_client
            self.short_cache_ttl = short_cache_ttl
            self.long_cache_ttl = long_cache_ttl
            self.remote_cache_key = "growthbook:feature_flags"
            self._cached_feature_flags = None

    def get_feature_flags_from_short_cache(self) -> dict:
        """
        Get feature flags from short cache
        """
        return self.cache_client.get(self.remote_cache_key)

    def get_feature_flags_from_long_cache(self) -> dict:
        """
        Get feature flags from long cache
        """
        return self.cache_client.get(self.remote_cache_key)

    def get_feature_flags_from_cache(self) -> dict:
        """
        Get feature flags from cache
        """
        # First, we check the short cache
        if short_cached_feature_flags := self.get_feature_flags_from_short_cache():
            return short_cached_feature_flags

        # TODO: Update the feature flags definitions (asynchronously)

        # If the short cache is not valid, we check the long cache
        # This exists as a safety net to avoid not having the feature flags
        # definitions if Growthbook's API is down for some reason.
        if long_cached_feature_flags := self.get_feature_flags_from_long_cache():
            self.set_feature_flags_to_short_cache(long_cached_feature_flags)
            return long_cached_feature_flags

        return None

    def set_feature_flags_to_short_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to short cache
        """
        self.cache_client.set(
            self.remote_cache_key, feature_flags, self.short_cache_ttl
        )

    def set_feature_flags_to_long_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to long cache
        """
        self.cache_client.set(self.remote_cache_key, feature_flags, self.long_cache_ttl)

    def set_feature_flags_to_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to cache
        """
        self.set_feature_flags_to_short_cache(feature_flags)
        self.set_feature_flags_to_long_cache(feature_flags)

    def update_feature_flags_definitions(self) -> dict:
        """
        Update feature flags definitions from Growthbook's API.
        """
        try:
            response = requests.get(
                f"{self.host_base_url}/api/features",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60,
            )
            response.raise_for_status()
            self.set_feature_flags_to_cache(response.json())
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to update feature flags definitions: %s",
                e,
            )
            capture_exception(e)

            raise e

        return response.json()

    def get_feature_flags(self) -> dict:
        """
        Get feature flags.
        """
        # If the cache is valid, we return it
        if cached_feature_flags := self.get_feature_flags_from_cache():
            return cached_feature_flags

        # If the cache is not valid, we update the feature flags definitions
        # This should not happen as we rely on the long cache to be valid,
        # but we'll handle it just in case.
        updated_feature_flags = self.update_feature_flags_definitions()

        return updated_feature_flags
