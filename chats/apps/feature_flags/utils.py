from typing import TYPE_CHECKING
from django.conf import settings
from chats.apps.feature_flags.services import FeatureFlagService


if TYPE_CHECKING:
    from chats.apps.accounts.models import User
    from chats.apps.projects.models.models import Project


def is_feature_active(feature_flag_key: str, user: "User", project: "Project") -> bool:
    """
    Check if a feature flag is active
    """
    if not settings.GROWTHBOOK_HOST_BASE_URL or not settings.GROWTHBOOK_CLIENT_KEY:
        return False

    return FeatureFlagService(GROWTHBOOK_CLIENT).evaluate_feature_flag(
        feature_flag_key, user=user, project=project
    )
