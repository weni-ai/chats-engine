import pickle
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from chats.apps.feedbacks.services import UserFeedbackService
from chats.apps.feature_flags.tests.mock import MockFeatureFlagService
from chats.core.tests.mock import MockCacheClient
from chats.apps.accounts.models import User


class TestUserFeedbackService(TestCase):
    def setUp(self):
        self.service = UserFeedbackService(
            cache_client=MockCacheClient(),
            feature_flags_service=MockFeatureFlagService(),
        )

    def test_get_feedback_form_shown_count_cache_key(self):
        current_date = timezone.now().date().isoformat()
        user = User.objects.create(email="test@test.com")
        cache_key = self.service.get_feedback_form_shown_count_cache_key(user)
        self.assertEqual(
            cache_key, f"feedback_form_shown_count:{user.id}:{current_date}"
        )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feedback_form_shown_count(self, mock_cache_get):
        mock_cache_get.return_value = 0
        user = User.objects.create(email="test@test.com")

        current_date = timezone.now().date().isoformat()

        self.service.get_feedback_form_shown_count(user)
        mock_cache_get.assert_called_once_with(
            f"feedback_form_shown_count:{user.id}:{current_date}",
        )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_increment_feedback_form_shown_count(self, mock_cache_set, mock_cache_get):
        mock_cache_get.return_value = 0
        user = User.objects.create(email="test@test.com")
        current_date = timezone.now().date().isoformat()

        self.service.increment_feedback_form_shown_count(user)
        mock_cache_set.assert_called_once_with(
            f"feedback_form_shown_count:{user.id}:{current_date}",
            1,
            ex=60 * 60 * 24,
        )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_survey_date_range_cached(self, mock_cache_get):
        dt = timezone.now().date()
        mock_cache_get.return_value = pickle.dumps((dt, dt))

        start_date, end_date = self.service.get_survey_date_range()

        self.assertEqual(start_date, dt)
        self.assertEqual(end_date, dt)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_get_survey_date_range_not_cached_and_no_rules(
        self, mock_cache_set, mock_cache_get
    ):
        mock_cache_get.return_value = None
        mock_cache_set.return_value = True

        dt = timezone.now().date()

        start_date, end_date = self.service.get_survey_date_range()

        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_get_survey_date_range_not_cached_and_rules(
        self, mock_cache_set, mock_cache_get
    ):
        mock_cache_get.return_value = None
        mock_cache_set.return_value = True

        dt = timezone.now()

        self.service.feature_flags_service.get_feature_flag_rules.return_value = [
            {
                "condition": {
                    "dateRange": {
                        "$in": [dt.isoformat(), dt.isoformat()],
                    },
                },
            },
        ]

        start_date, end_date = self.service.get_survey_date_range()

        self.assertEqual(start_date, dt)
        self.assertEqual(end_date, dt)

        self.service.feature_flags_service.get_feature_flag_rules.assert_called_once_with(
            self.service.feedback_feature_flag_key
        )
