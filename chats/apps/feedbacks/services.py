import pickle
from abc import ABC, abstractmethod
from datetime import datetime
import logging

from django.conf import settings
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.feature_flags.services import FeatureFlagService
from chats.core.cache import CacheClient
from chats.apps.feedbacks.models import LastFeedbackShownToUser
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


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
        self.feedback_feature_flag_key = settings.FEEDBACK_FEATURE_FLAG_KEY

    def get_feedback_form_shown_count_cache_key(self, user: User) -> str:
        """
        Get feedback form shown count cache key
        """
        current_date = timezone.now().date().isoformat()  # YYYY-MM-DD

        return f"feedback_form_shown_count_{user.id}_{current_date}"

    def get_feedback_form_shown_count(self, user: User) -> dict:
        """
        Get feedback form shown count data
        """
        return self.cache_client.get(
            self.get_feedback_form_shown_count_cache_key(user),
            0,
        )

    def increment_feedback_form_shown_count(self, user: User) -> int:
        """
        Increment feedback form shown count
        """
        current_count = self.get_feedback_form_shown_count(user)

        self.cache_client.set(
            self.get_feedback_form_shown_count_cache_key(user),
            current_count + 1,
            ex=(60 * 60 * 24),  # 24 hours
        )

    def get_survey_date_range(self) -> tuple[datetime.date, datetime.date]:
        """
        Get survey date range
        """
        cache_key = "user_feedback_survey_date_range"

        cached_date_range = self.cache_client.get(cache_key)

        if cached_date_range:
            try:
                return pickle.loads(cached_date_range)
            except Exception as e:
                logger.error(
                    "Error loading cached survey date range: %s",
                    e,
                )

        rules = self.feature_flags_service.get_feature_flag_rules(
            self.feedback_feature_flag_key
        )

        if not rules:
            return None, None

        survey_rule = None

        for rule in rules:
            if rule.get("condition", {}).get("dateRange", None) is not None:
                survey_rule = rule
                break

        if not survey_rule:
            return None, None

        dates = survey_rule.get("condition", {}).get("dateRange", [])

        if len(dates) != 2:
            return None, None

        dates = sorted(dates)

        start_date = datetime.fromisoformat(dates[0])
        end_date = datetime.fromisoformat(dates[1])

        self.cache_client.set(
            cache_key,
            pickle.dumps((start_date, end_date)),
            ex=10,  # 10 seconds
        )

        return start_date, end_date

    def should_show_feedback_form(self, user: User) -> bool:
        """
        Should show feedback form
        """
        shown_count = self.get_feedback_form_shown_count(user)

        if shown_count >= 2:
            return False

        start_date, end_date = self.get_survey_date_range()

        if not start_date or not end_date:
            return False

        now = timezone.now()

        if now > end_date or now < start_date:
            return False

        query = {
            "user": user,
            "is_active": False,
        }

        last_shown = LastFeedbackShownToUser.objects.filter(user=user).first()

        if last_shown and last_shown.last_shown_at > start_date:
            query["ended_at__gte"] = last_shown.last_shown_at

        else:
            query["ended_at__gte"] = start_date

        rooms_count = Room.objects.filter(**query)

        if rooms_count > 15:
            if not last_shown:
                LastFeedbackShownToUser.objects.create(
                    user=user,
                    last_shown_at=timezone.now(),
                )
            else:
                last_shown.last_shown_at = timezone.now()
                last_shown.save(update_fields=["last_shown_at"])

            self.increment_feedback_form_shown_count(user)

            return True

        return False
