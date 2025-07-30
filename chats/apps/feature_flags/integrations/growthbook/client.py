from abc import ABC, abstractmethod
import threading
import requests
import logging
from sentry_sdk import capture_exception

from django.utils import timezone
from django.utils.timezone import timedelta

from chats.core.cache import CacheClient


logger = logging.getLogger(__name__)


class BaseGrowthbookClient(ABC):
    """
    Base class for Growthbook client.
    """

    @abstractmethod
    def get_feature_flags_from_local_cache(self) -> None:
        """
        Get feature flags from local cache
        """
        raise NotImplementedError

    @abstractmethod
    def set_feature_flags_to_local_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to local cache
        """
        raise NotImplementedError

    @abstractmethod
    def get_feature_flags_from_remote_cache(self) -> None:
        """
        Get feature flags from cache
        """
        raise NotImplementedError

    @abstractmethod
    def set_feature_flags_to_remote_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to remote cache
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
        local_cache_ttl: int,
        remote_cache_client: CacheClient,
        remote_short_cache_ttl: int,
        remote_long_cache_ttl: int,
    ):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.host_base_url = host_base_url
                cls._instance.api_key = api_key
                cls._instance.local_cache_ttl = local_cache_ttl
                cls._instance.remote_cache_client = remote_cache_client
                cls._instance.remote_short_cache_ttl = remote_short_cache_ttl
                cls._instance.remote_long_cache_ttl = remote_long_cache_ttl
                cls._instance._last_local_update = None
        return cls._instance

    def __init__(
        self,
        host_base_url: str,
        api_key: str,
        local_cache_ttl: int,
        remote_cache_client: CacheClient,
        remote_short_cache_ttl: int,
        remote_long_cache_ttl: int,
    ):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.host_base_url = host_base_url
            self.api_key = api_key
            self.local_cache_ttl = local_cache_ttl
            self.remote_cache_client: CacheClient = remote_cache_client
            self.remote_short_cache_ttl = remote_short_cache_ttl
            self.remote_long_cache_ttl = remote_long_cache_ttl
            self.remote_cache_key = "growthbook:feature_flags"
            self._last_local_update = None
            self._cached_feature_flags = None

    def get_feature_flags_from_local_cache(self) -> dict:
        """
        Get feature flags from local cache
        """
        if (
            self._last_local_update is None
            or self._last_local_update + timedelta(seconds=self.local_cache_ttl)
            < timezone.now()
        ):
            return None

        return self._cached_feature_flags

    def set_feature_flags_to_local_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to local cache
        """
        self._cached_feature_flags = feature_flags
        self._last_local_update = timezone.now()

    def get_feature_flags_from_short_remote_cache(self) -> dict:
        """
        Get feature flags from short remote cache
        """
        return self.remote_cache_client.get(self.remote_cache_key)

    def get_feature_flags_from_long_remote_cache(self) -> dict:
        """
        Get feature flags from long remote cache
        """
        return self.remote_cache_client.get(self.remote_cache_key)

    def get_feature_flags_from_remote_cache(self) -> dict:
        """
        Get feature flags from remote cache
        """
        # First, we check the short cache
        if (
            short_cached_feature_flags := self.get_feature_flags_from_short_remote_cache()
        ):
            return short_cached_feature_flags

        # TODO: Update the feature flags definitions (asynchronously)

        # If the short cache is not valid, we check the long cache
        # This exists as a safety net to avoid not having the feature flags
        # definitions if Growthbook's API is down for some reason.
        if long_cached_feature_flags := self.get_feature_flags_from_long_remote_cache():
            self.set_feature_flags_to_short_remote_cache(long_cached_feature_flags)
            return long_cached_feature_flags

        return None

    def set_feature_flags_to_short_remote_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to short remote cache
        """
        self.remote_cache_client.set(
            self.remote_cache_key, feature_flags, self.remote_short_cache_ttl
        )

    def set_feature_flags_to_long_remote_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to remote cache
        """
        self.remote_cache_client.set(
            self.remote_cache_key, feature_flags, self.remote_long_cache_ttl
        )

    def set_feature_flags_to_remote_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to remote cache
        """
        self.set_feature_flags_to_short_remote_cache(feature_flags)
        self.set_feature_flags_to_long_remote_cache(feature_flags)

    def update_feature_flags_definitions(self) -> None:
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
            self.set_feature_flags_to_remote_cache(response.json())
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to update feature flags definitions: %s",
                e,
            )
            capture_exception(e)

    def get_feature_flags(self) -> dict:
        """
        Get feature flags.
        """
        # If the local cache is still valid, we return it here
        if local_cached_feature_flags := self.get_feature_flags_from_local_cache():
            return local_cached_feature_flags

        # But if the local cache is not valid, we check the remote cache
        if remote_cached_feature_flags := self.get_feature_flags_from_remote_cache():
            self.set_feature_flags_to_local_cache(remote_cached_feature_flags)

            return self.get_feature_flags_from_local_cache()

        # If the remote cache is not valid, we update the feature flags definitions
        self.update_feature_flags_definitions()

        return self.get_feature_flags_from_local_cache()
