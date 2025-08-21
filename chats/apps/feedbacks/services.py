from abc import ABC, abstractmethod
from datetime import datetime

from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.feature_flags.services import FeatureFlagService
from chats.core.cache import CacheClient


class BaseUserFeedbackService(ABC):
    """
    Base user feedback service
    """

    @abstractmethod
    def get_feedback_form_shown_count_cache_key(self, user: User) -> str:
        pass

    @abstractmethod
    def get_feedback_form_shown_count(self, user: User) -> int:
        pass

    @abstractmethod
    def get_survey_date_range(self) -> tuple[datetime.date, datetime.date]:
        pass

    @abstractmethod
    def should_show_feedback_form(self, user: User) -> bool:
        pass


class UserFeedbackService(BaseUserFeedbackService):
    """
    User feedback service
    """

    def __init__(
        self, cache_client: CacheClient, feature_flags_service: FeatureFlagService
    ):
        self.cache_client = cache_client
        self.feature_flags_service = feature_flags_service

    def get_feedback_form_shown_count_cache_key(self, user: User) -> str:
        """
        Get feedback form shown count cache key
        """
        current_date = timezone.now().date().isoformat()  # YYYY-MM-DD

        return f"feedback_form_shown_count_{user.id}_{current_date}"

    def get_feedback_form_shown_count_data(self, user: User) -> dict:
        """
        Get feedback form shown count data
        """
        return self.cache_client.get(
            self.get_feedback_form_shown_count_cache_key(user),
            {
                "count": 0,
                "last_shown_at": None,
            },
        )

    def increment_feedback_form_shown_count(self, user: User) -> int:
        """
        Increment feedback form shown count
        """
        current_count_data = self.get_feedback_form_shown_count_data(user)

        self.cache_client.set(
            self.get_feedback_form_shown_count_cache_key(user),
            {
                "count": current_count_data.get("count", 0) + 1,
                "last_shown_at": timezone.now(),
            },
        )

    def get_survey_date_range(self) -> tuple[datetime.date, datetime.date]:
        """
        Get survey date range
        """

    def should_show_feedback_form(self, user: User) -> bool:
        """
        Should show feedback form
        """
        shown_count_data = self.get_feedback_form_shown_count_data(user)

        if shown_count_data.get("count", 0) >= 2:
            return False

        # TODO: Continue
