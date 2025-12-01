from weni.feature_flags.services import FeatureFlagsService as WeniFeatureFlagsService

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project


class FeatureFlagService:
    """
    Wrapper service for weni-commons feature flags service.
    Adapts the weni-commons API to the chats-engine interface.
    """

    def __init__(self, feature_flags_service: WeniFeatureFlagsService = None):
        self.feature_flags_service = feature_flags_service or WeniFeatureFlagsService()

    def get_feature_flags_list_for_user_and_project(self, user: User, project: Project):
        """
        Get feature flags list for user and project.
        """
        attributes = {
            "userEmail": user.email,
            "projectUUID": str(project.uuid),
        }

        return self.feature_flags_service.get_active_feature_flags_for_attributes(
            attributes
        )

    def evaluate_feature_flag(
        self, key: str, user: User = None, project: Project = None
    ) -> bool:
        """
        Evaluate feature flag by project.
        """
        attributes = {}

        if user:
            attributes["userEmail"] = user.email
        if project:
            attributes["projectUUID"] = str(project.uuid)

        if not attributes:
            raise ValueError("No attributes provided to evaluate feature flag")

        return self.feature_flags_service.evaluate_feature_flag_by_attributes(
            key, attributes
        )

    def get_feature_flag_rules(self, key: str) -> dict:
        """
        Get feature flag rules
        """
        feature_flags = self.feature_flags_service.get_feature_flags()

        return feature_flags.get(key, {}).get("rules", [])
