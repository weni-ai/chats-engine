from abc import ABC, abstractmethod
import json
import threading
import requests
import logging

from sentry_sdk import capture_exception
from growthbook import GrowthBook

from chats.core.cache import CacheClient
from chats.apps.feature_flags.integrations.growthbook.tasks import (
    update_growthbook_feature_flags,
)


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
    def flush_short_cache(self) -> None:
        """
        Flush short cache
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

    @abstractmethod
    def get_active_feature_flags_for_attributes(self, attributes: dict) -> list[str]:
        """
        Evaluate features by attributes.
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate_feature_flag_by_attributes(self, key: str, attributes: dict) -> bool:
        """
        Evaluate feature flag by attributes.
        """
        raise NotImplementedError


class GrowthbookClient(BaseGrowthbookClient):
    _instance = None
    _lock = threading.Lock()

    def __new__(
        cls,
        host_base_url: str,
        client_key: str,
        cache_client: CacheClient,
        short_cache_key: str,
        short_cache_ttl: int,
        long_cache_key: str,
        long_cache_ttl: int,
        is_singleton: bool = False,
    ):
        with cls._lock:
            if cls._instance is None or is_singleton is False:
                cls._instance = super().__new__(cls)
                cls._instance.host_base_url = host_base_url
                cls._instance.client_key = client_key
                cls._instance.cache_client = cache_client
                cls._instance.short_cache_key = short_cache_key
                cls._instance.short_cache_ttl = short_cache_ttl
                cls._instance.long_cache_key = long_cache_key
                cls._instance.long_cache_ttl = long_cache_ttl
                cls._instance.is_singleton = is_singleton
        return cls._instance

    def __init__(
        self,
        host_base_url: str,
        client_key: str,
        cache_client: CacheClient,
        short_cache_key: str,
        short_cache_ttl: int,
        long_cache_key: str,
        long_cache_ttl: int,
        is_singleton: bool = False,
    ):
        if getattr(self, "_initialized", False) is False:
            assert (
                short_cache_ttl < long_cache_ttl
            ), "Short cache TTL must be less than long cache TTL"

            self._initialized = True if is_singleton is True else False
            self.host_base_url = host_base_url
            self.client_key = client_key
            self.cache_client: CacheClient = cache_client
            self.short_cache_key = short_cache_key
            self.short_cache_ttl = short_cache_ttl
            self.long_cache_key = long_cache_key
            self.long_cache_ttl = long_cache_ttl

    def get_feature_flags_from_short_cache(self) -> dict:
        """
        Get feature flags from short cache
        """
        cached_feature_flags = self.cache_client.get(self.short_cache_key)

        if not cached_feature_flags:
            return None

        if not isinstance(cached_feature_flags, dict):
            try:
                cached_feature_flags = json.loads(cached_feature_flags)
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse feature flags from short cache: %s",
                    cached_feature_flags,
                )
                capture_exception(e)
                return None

        return cached_feature_flags

    def get_feature_flags_from_long_cache(self) -> dict:
        """
        Get feature flags from long cache
        """
        cached_feature_flags = self.cache_client.get(self.long_cache_key)

        if not cached_feature_flags:
            return None

        if not isinstance(cached_feature_flags, dict):
            try:
                cached_feature_flags = json.loads(cached_feature_flags)
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse feature flags from long cache: %s",
                    cached_feature_flags,
                )
                capture_exception(e)
                return None

        return cached_feature_flags

    def get_feature_flags_from_cache(self) -> dict:
        """
        Get feature flags from cache
        """
        # First, we check the short cache
        if short_cached_feature_flags := self.get_feature_flags_from_short_cache():
            return short_cached_feature_flags

        # If the short cache is not valid, this means that is time
        # to update the feature flags definitions.
        # This is done asynchronously and we return the long cache as a fallback.
        update_growthbook_feature_flags.delay()

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
            self.short_cache_key,
            json.dumps(feature_flags, ensure_ascii=False),
            self.short_cache_ttl,
        )

    def flush_short_cache(self) -> None:
        """
        Flush short cache
        """
        self.cache_client.delete(self.short_cache_key)

    def set_feature_flags_to_long_cache(self, feature_flags: dict) -> None:
        """
        Set feature flags to long cache
        """
        self.cache_client.set(
            self.long_cache_key,
            json.dumps(feature_flags, ensure_ascii=False),
            self.long_cache_ttl,
        )

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
                f"{self.host_base_url}/api/features/{self.client_key}",
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

    def get_active_feature_flags_for_attributes(self, attributes: dict) -> list[str]:
        """
        Evaluate features by attributes.
        """
        all_features = self.get_feature_flags()

        gb = GrowthBook(
            attributes=attributes,
            features=all_features,
        )

        active_features = []

        for key in all_features.keys():
            if gb.eval_feature(key).on:
                active_features.append(key)

        return active_features

    def evaluate_feature_flag_by_attributes(self, key: str, attributes: dict) -> bool:
        """
        Evaluate feature flag by attributes.
        """
        all_features = self.get_feature_flags()

        gb = GrowthBook(
            attributes=attributes,
            features=all_features,
        )

        return gb.eval_feature(key).on
