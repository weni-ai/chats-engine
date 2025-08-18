from unittest.mock import MagicMock

from chats.apps.feature_flags.integrations.growthbook.clients import (
    BaseGrowthbookClient,
)


class MockGrowthbookClient(BaseGrowthbookClient):
    """
    Mock growthbook client.
    """

    def get_feature_flags_from_short_cache(self) -> dict:
        return {}

    def get_feature_flags_from_long_cache(self) -> dict:
        return {}

    def get_feature_flags_from_cache(self) -> dict:
        return {}

    def set_feature_flags_to_short_cache(self, feature_flags: dict) -> None:
        pass

    def flush_short_cache(self) -> None:
        pass

    def set_feature_flags_to_long_cache(self, feature_flags: dict) -> None:
        pass

    def set_feature_flags_to_cache(self, feature_flags: dict) -> None:
        pass

    def update_feature_flags_definitions(self) -> dict:
        return {}

    def get_feature_flags(self) -> dict:
        return {}

    def evaluate_features_by_attributes(self, attributes: dict) -> list[str]:
        return []

    def __init__(self):
        # Create mock methods that can be used for assertions
        self.get_feature_flags_from_short_cache = MagicMock(return_value={})
        self.get_feature_flags_from_long_cache = MagicMock(return_value={})
        self.get_feature_flags_from_cache = MagicMock(return_value={})
        self.set_feature_flags_to_short_cache = MagicMock()
        self.flush_short_cache = MagicMock()
        self.set_feature_flags_to_long_cache = MagicMock()
        self.set_feature_flags_to_cache = MagicMock()
        self.update_feature_flags_definitions = MagicMock(return_value={})
        self.get_feature_flags = MagicMock(return_value={})
        self.evaluate_features_by_attributes = MagicMock(return_value=[])
