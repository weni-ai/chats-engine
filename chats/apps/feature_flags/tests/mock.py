from unittest.mock import MagicMock


class MockFeatureFlagService:
    """
    Mock feature flag service
    """

    def __init__(self):
        self.get_feature_flags_list_for_user_and_project = MagicMock(return_value=[])
        self.evaluate_feature_flag = MagicMock(return_value=False)
        self.get_feature_flag_rules = MagicMock(return_value=[])
