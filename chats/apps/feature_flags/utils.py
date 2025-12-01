from typing import TYPE_CHECKING
from chats.apps.feature_flags.services import FeatureFlagService


if TYPE_CHECKING:
    from chats.apps.accounts.models import User
    from chats.apps.projects.models.models import Project


def is_feature_active(feature_flag_key: str, user: "User", project: "Project") -> bool:
    """
    Check if a feature flag is active
    """
    return FeatureFlagService().evaluate_feature_flag(
        feature_flag_key, user=user, project=project
    )
