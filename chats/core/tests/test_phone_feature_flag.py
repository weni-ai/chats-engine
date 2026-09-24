from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from chats.core.phone import (
    is_ninth_digit_search_enabled,
    ninth_digit_search_enabled_from_request,
)


class IsNinthDigitSearchEnabledTests(SimpleTestCase):
    def test_returns_false_when_project_uuid_is_missing(self):
        self.assertFalse(is_ninth_digit_search_enabled(user_email="a@b.com"))
        self.assertFalse(is_ninth_digit_search_enabled(project_uuid=None))

    @patch("chats.core.phone.is_feature_active", return_value=True)
    def test_uses_user_email_when_provided(self, mock_is_feature_active):
        result = is_ninth_digit_search_enabled(
            user_email="agent@example.com",
            project_uuid="proj-uuid",
        )

        self.assertTrue(result)
        mock_is_feature_active.assert_called_once()
        args = mock_is_feature_active.call_args[0]
        self.assertEqual(args[1], "agent@example.com")
        self.assertEqual(args[2], "proj-uuid")

    @patch("chats.core.phone.is_feature_active_for_attributes", return_value=False)
    def test_uses_project_attributes_when_email_is_missing(self, mock_for_attributes):
        result = is_ninth_digit_search_enabled(project_uuid="proj-uuid")

        self.assertFalse(result)
        mock_for_attributes.assert_called_once()
        self.assertEqual(
            mock_for_attributes.call_args[0][1],
            {"projectUUID": "proj-uuid"},
        )

    @patch("chats.core.phone.is_feature_active", side_effect=RuntimeError("ff down"))
    def test_returns_false_when_feature_flag_raises(self, _mock_is_feature_active):
        result = is_ninth_digit_search_enabled(
            user_email="agent@example.com",
            project_uuid="proj-uuid",
        )

        self.assertFalse(result)


class NinthDigitSearchEnabledFromRequestTests(SimpleTestCase):
    def test_returns_false_when_request_is_none(self):
        self.assertFalse(ninth_digit_search_enabled_from_request(None))

    def test_returns_cached_value_from_request(self):
        request = MagicMock()
        request._ninth_digit_search_flag = True

        self.assertTrue(ninth_digit_search_enabled_from_request(request))

    @patch("chats.core.phone.is_ninth_digit_search_enabled", return_value=True)
    def test_reads_project_and_authenticated_user_from_request(
        self, mock_is_enabled
    ):
        request = MagicMock(spec=["query_params", "user"])
        request.query_params = {"project": "proj-uuid"}
        request.user.is_authenticated = True
        request.user.email = "agent@example.com"

        result = ninth_digit_search_enabled_from_request(request)

        self.assertTrue(result)
        mock_is_enabled.assert_called_once_with(
            user_email="agent@example.com",
            project_uuid="proj-uuid",
        )
        self.assertTrue(request._ninth_digit_search_flag)

    @patch("chats.core.phone.is_ninth_digit_search_enabled", return_value=False)
    def test_ignores_email_when_user_is_not_authenticated(self, mock_is_enabled):
        request = MagicMock(spec=["GET", "user"])
        request.GET = {"project": "proj-uuid"}
        request.user.is_authenticated = False
        request.user.email = "agent@example.com"

        result = ninth_digit_search_enabled_from_request(request)

        self.assertFalse(result)
        mock_is_enabled.assert_called_once_with(
            user_email=None,
            project_uuid="proj-uuid",
        )
