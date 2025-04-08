import logging
from typing import Any, Dict

from django.conf import settings
from growthbook import GrowthBook

logger = logging.getLogger(__name__)


class GrowthBookClient:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GrowthBookClient, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_client(cls):
        if cls._instance is None:
            api_host = getattr(
                settings, "GROWTHBOOK_API_HOST", "https://cdn.growthbook.io"
            )
            client_key = getattr(settings, "GROWTHBOOK_CLIENT_KEY", None)
            enabled = getattr(settings, "GROWTHBOOK_ENABLED", False)
            if not client_key:
                logger.info("GrowthBook is disabled or missing client_key")
                cls._client = None
            else:
                try:
                    cls._client = GrowthBook(
                        api_host=api_host, client_key=client_key, enabled=enabled, attributes={}
                    )
                    cls._client.load_features()
                    logger.info("GrowthBook initialized successfully")
                except Exception as e:
                    logger.error(f"Error initializing GrowthBook: {e}")
                    cls._client = None
            cls._instance = cls()
        return cls._client

    @classmethod
    def set_attributes(cls, attributes: Dict[str, Any]) -> None:
        client = cls.get_client()
        if client:
            client.set_attributes(attributes)

    @classmethod
    def is_on(cls, feature_key: str, default: bool = False) -> bool:
        client = cls.get_client()
        if not client:
            return default
        return client.is_on(feature_key)

    @classmethod
    def is_off(cls, feature_key: str) -> bool:
        client = cls.get_client()
        if not client:
            return True
        return client.is_off(feature_key)

    @classmethod
    def get_feature_value(cls, feature_key: str, default: Any = None) -> Any:
        client = cls.get_client()
        if not client:
            return default
        return client.get_feature_value(feature_key, default)


def get_growthbook():
    return GrowthBookClient.get_client()
