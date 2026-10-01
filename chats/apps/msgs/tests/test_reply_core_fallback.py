from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from chats.apps.msgs.utils import extract_wamid_core, is_reply_core_fallback_active


class IsReplyCoreFallbackActiveTests(SimpleTestCase):
    def test_returns_false_when_project_uuid_is_missing(self):
        self.assertFalse(is_reply_core_fallback_active(None))
        self.assertFalse(is_reply_core_fallback_active(""))

    @override_settings(REPLY_CORE_FALLBACK_FEATURE_FLAG_KEY="flag-key")
    @patch("chats.apps.msgs.utils.is_feature_active_for_attributes", return_value=True)
    def test_returns_flag_value(self, mock_flag):
        self.assertTrue(is_reply_core_fallback_active("project-1"))
        mock_flag.assert_called_once_with("flag-key", {"projectUUID": "project-1"})

    @override_settings(REPLY_CORE_FALLBACK_FEATURE_FLAG_KEY="flag-key")
    @patch("chats.apps.msgs.utils.capture_exception")
    @patch(
        "chats.apps.msgs.utils.is_feature_active_for_attributes",
        side_effect=RuntimeError("flag down"),
    )
    def test_returns_false_when_flag_service_fails(self, mock_flag, mock_capture):
        self.assertFalse(is_reply_core_fallback_active("project-1"))
        mock_capture.assert_called_once()


class ExtractWamidCoreTests(SimpleTestCase):
    def test_returns_none_for_invalid_input(self):
        self.assertIsNone(extract_wamid_core(None))
        self.assertIsNone(extract_wamid_core(""))
        self.assertIsNone(extract_wamid_core(123))
        self.assertIsNone(extract_wamid_core("not-a-wamid"))
