import pickle
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.feedbacks.models import LastFeedbackShownToUser
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

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    def test_can_create_feedback_when_shown_count_is_2(
        self, mock_get_feedback_form_shown_count
    ):
        mock_get_feedback_form_shown_count.return_value = 2
        user = User.objects.create(email="test@test.com")

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    def test_can_create_feedback_when_shown_count_is_less_than_2_and_survey_date_range_is_not_set(
        self, mock_get_survey_date_range, mock_get_feedback_form_shown_count
    ):
        mock_get_feedback_form_shown_count.return_value = 0
        mock_get_survey_date_range.return_value = (None, None)
        user = User.objects.create(email="test@test.com")

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    def test_can_create_feedback_when_survey_date_range_is_set_but_in_the_past(
        self, mock_get_survey_date_range, mock_get_feedback_form_shown_count
    ):
        mock_get_feedback_form_shown_count.return_value = 0
        start_date = timezone.now() - timedelta(days=2)
        end_date = timezone.now() - timedelta(days=1)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    def test_can_create_feedback_when_survey_date_range_is_set_and_in_the_future(
        self, mock_get_survey_date_range, mock_get_feedback_form_shown_count
    ):
        mock_get_feedback_form_shown_count.return_value = 0
        start_date = timezone.now() + timedelta(days=1)
        end_date = timezone.now() + timedelta(days=2)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    @patch("chats.apps.feedbacks.services.UserFeedback.objects.filter")
    def test_can_create_feedback_when_user_already_answered_feedback_in_the_past(
        self,
        mock_user_feedback_filter,
        mock_get_survey_date_range,
        mock_get_feedback_form_shown_count,
    ):
        mock_get_feedback_form_shown_count.return_value = 0
        start_date = timezone.now() - timedelta(days=1)
        end_date = timezone.now() + timedelta(days=2)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        mock_user_feedback_filter.return_value.exists.return_value = True

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()
        mock_user_feedback_filter.assert_called_once_with(
            user=user,
            answered_at__gte=start_date,
        )

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    @patch("chats.apps.feedbacks.services.UserFeedback.objects.filter")
    @patch("chats.apps.feedbacks.services.LastFeedbackShownToUser.objects.filter")
    @patch("chats.apps.feedbacks.services.Room.objects.filter")
    def test_can_create_feedback_when_user_has_no_shown_feedback_yet_and_does_not_have_enough_rooms(
        self,
        mock_room_filter,
        mock_last_feedback_shown_to_user_filter,
        mock_user_feedback_filter,
        mock_get_survey_date_range,
        mock_get_feedback_form_shown_count,
    ):
        mock_get_feedback_form_shown_count.return_value = 0
        start_date = timezone.now() - timedelta(days=1)
        end_date = timezone.now() + timedelta(days=2)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        mock_user_feedback_filter.return_value.exists.return_value = False
        mock_last_feedback_shown_to_user_filter.return_value.first.return_value = None
        mock_room_filter.return_value.count.return_value = 14

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()
        mock_user_feedback_filter.assert_called_once_with(
            user=user,
            answered_at__gte=start_date,
        )
        mock_last_feedback_shown_to_user_filter.assert_called_once_with(user=user)
        mock_room_filter.assert_called_once_with(
            user=user,
            is_active=False,
            ended_at__gte=start_date,
        )

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    @patch("chats.apps.feedbacks.services.UserFeedback.objects.filter")
    @patch("chats.apps.feedbacks.services.LastFeedbackShownToUser.objects.filter")
    @patch("chats.apps.feedbacks.services.Room.objects.filter")
    def test_can_create_feedback_when_user_has_no_shown_feedback_yet_and_does_have_enough_rooms(
        self,
        mock_room_filter,
        mock_last_feedback_shown_to_user_filter,
        mock_user_feedback_filter,
        mock_get_survey_date_range,
        mock_get_feedback_form_shown_count,
    ):
        mock_get_feedback_form_shown_count.return_value = 0
        start_date = timezone.now() - timedelta(days=1)
        end_date = timezone.now() + timedelta(days=2)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        mock_user_feedback_filter.return_value.exists.return_value = False
        mock_last_feedback_shown_to_user_filter.return_value.first.return_value = None
        mock_room_filter.return_value.count.return_value = 15

        self.assertTrue(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()
        mock_user_feedback_filter.assert_called_once_with(
            user=user,
            answered_at__gte=start_date,
        )
        mock_last_feedback_shown_to_user_filter.assert_called_once_with(user=user)
        mock_room_filter.assert_called_once_with(
            user=user,
            is_active=False,
            ended_at__gte=start_date,
        )

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    @patch("chats.apps.feedbacks.services.UserFeedback.objects.filter")
    @patch("chats.apps.feedbacks.services.LastFeedbackShownToUser.objects.filter")
    @patch("chats.apps.feedbacks.services.Room.objects.filter")
    def test_can_create_feedback_when_user_has_shown_feedback_yet_and_does_not_have_enough_rooms(
        self,
        mock_room_filter,
        mock_last_feedback_shown_to_user_filter,
        mock_user_feedback_filter,
        mock_get_survey_date_range,
        mock_get_feedback_form_shown_count,
    ):
        mock_get_feedback_form_shown_count.return_value = 1
        start_date = timezone.now() - timedelta(days=1)
        end_date = timezone.now() + timedelta(days=2)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        mock_user_feedback_filter.return_value.exists.return_value = False

        last_shown = LastFeedbackShownToUser.objects.create(
            user=user,
            last_shown_at=timezone.now(),
        )

        mock_last_feedback_shown_to_user_filter.return_value.first.return_value = (
            last_shown
        )
        mock_room_filter.return_value.count.return_value = 14

        self.assertFalse(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()
        mock_user_feedback_filter.assert_called_once_with(
            user=user,
            answered_at__gte=start_date,
        )
        mock_last_feedback_shown_to_user_filter.assert_called_once_with(user=user)
        mock_room_filter.assert_called_once_with(
            user=user,
            is_active=False,
            ended_at__gte=last_shown.last_shown_at,
        )

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.get_feedback_form_shown_count"
    )
    @patch("chats.apps.feedbacks.services.UserFeedbackService.get_survey_date_range")
    @patch("chats.apps.feedbacks.services.UserFeedback.objects.filter")
    @patch("chats.apps.feedbacks.services.LastFeedbackShownToUser.objects.filter")
    @patch("chats.apps.feedbacks.services.Room.objects.filter")
    def test_can_create_feedback_when_user_has_shown_feedback_yet_and_does_not_enough_rooms(
        self,
        mock_room_filter,
        mock_last_feedback_shown_to_user_filter,
        mock_user_feedback_filter,
        mock_get_survey_date_range,
        mock_get_feedback_form_shown_count,
    ):
        mock_get_feedback_form_shown_count.return_value = 1
        start_date = timezone.now() - timedelta(days=1)
        end_date = timezone.now() + timedelta(days=2)
        mock_get_survey_date_range.return_value = (start_date, end_date)
        user = User.objects.create(email="test@test.com")

        mock_user_feedback_filter.return_value.exists.return_value = False

        last_shown = LastFeedbackShownToUser.objects.create(
            user=user,
            last_shown_at=timezone.now(),
        )

        mock_last_feedback_shown_to_user_filter.return_value.first.return_value = (
            last_shown
        )
        mock_room_filter.return_value.count.return_value = 15

        self.assertTrue(self.service.can_create_feedback(user))

        mock_get_feedback_form_shown_count.assert_called_once_with(user)
        mock_get_survey_date_range.assert_called_once()
        mock_user_feedback_filter.assert_called_once_with(
            user=user,
            answered_at__gte=start_date,
        )
        mock_last_feedback_shown_to_user_filter.assert_called_once_with(user=user)
        mock_room_filter.assert_called_once_with(
            user=user,
            is_active=False,
            ended_at__gte=last_shown.last_shown_at,
        )
