from unittest.mock import MagicMock

from chats.apps.accounts.models import User
from chats.apps.feature_flags.services import BaseFeatureFlagService
from chats.apps.projects.models.models import Project


class MockFeatureFlagService(BaseFeatureFlagService):
    """
    Mock feature flag service
    """

    def get_feature_flags_list_for_user_and_project(self, user: User, project: Project):
        """
        Get feature flags list for user and project
        """
        return []

    def evaluate_feature_flag(
        self, key: str, user: User = None, project: Project = None
    ) -> bool:
        """
        Evaluate feature flag
        """
        return False

    def get_feature_flag_rules(self, key: str):
        """
        Get feature flag rules
        """
        return []

    def __init__(self):
        self.get_feature_flags_list_for_user_and_project = MagicMock(return_value=[])
        self.evaluate_feature_flag = MagicMock(return_value=False)
        self.get_feature_flag_rules = MagicMock(return_value=[])
