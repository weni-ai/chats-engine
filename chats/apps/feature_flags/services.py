from abc import ABC, abstractmethod

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.feature_flags.integrations.growthbook.instance import GROWTHBOOK_CLIENT


class BaseFeatureFlagService(ABC):
    """
    Base service for feature flags.
    """

    @abstractmethod
    def get_feature_flags_list(self) -> list[str]:
        """
        Get feature flags list.
        """
        raise NotImplementedError


class FeatureFlagService(BaseFeatureFlagService):
    """
    Service for getting feature flags list.
    """

    def get_feature_flags_list_for_user_and_project(
        self, user: User, project: Project
    ) -> list[str]:
        """
        Get feature flags list for user and project.
        """
        attributes = {
            "userEmail": user.email,
            "projectUUID": project.uuid,
        }

        return GROWTHBOOK_CLIENT.evaluate_features_by_attributes(attributes)
