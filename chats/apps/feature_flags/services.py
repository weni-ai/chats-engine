from abc import ABC, abstractmethod

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.feature_flags.integrations.growthbook.instance import GROWTHBOOK_CLIENT
from chats.apps.feature_flags.integrations.growthbook.clients import (
    BaseGrowthbookClient,
)


class BaseFeatureFlagService(ABC):
    """
    Base service for feature flags.
    """

    @abstractmethod
    def get_feature_flags_list_for_user_and_project(
        self, user: User, project: Project
    ) -> list[str]:
        """
        Get feature flags list.
        """
        raise NotImplementedError


class FeatureFlagService(BaseFeatureFlagService):
    """
    Service for getting feature flags list.
    """

    def __init__(self, growthbook_client: BaseGrowthbookClient = GROWTHBOOK_CLIENT):
        self.growthbook_client = growthbook_client

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

        return self.growthbook_client.get_active_feature_flags_for_attributes(
            attributes
        )

    def evaluate_feature_flag_by_project(self, key: str, project: Project) -> bool:
        """
        Evaluate feature flag by project.
        """
        attributes = {
            "projectUUID": project.uuid,
        }

        return self.growthbook_client.evaluate_feature_flag_by_attributes(
            key, attributes
        )
