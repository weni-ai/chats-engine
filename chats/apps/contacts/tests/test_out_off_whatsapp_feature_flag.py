from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import SimpleTestCase

from chats.apps.contacts.feature_flags import (
    is_out_off_whatsapp_response_window_enabled,
)


class OutOffWhatsappResponseWindowFeatureFlagTests(SimpleTestCase):
    def test_missing_project_is_off(self):
        self.assertFalse(is_out_off_whatsapp_response_window_enabled(None))
        self.assertFalse(is_out_off_whatsapp_response_window_enabled(""))

    @patch("chats.apps.contacts.feature_flags.is_feature_active_for_attributes")
    def test_evaluates_the_project_uuid(self, mock_flag):
        mock_flag.return_value = True
        project_uuid = uuid4()

        enabled = is_out_off_whatsapp_response_window_enabled(project_uuid)

        self.assertTrue(enabled)
        key, attributes = mock_flag.call_args[0]
        self.assertEqual(
            key, settings.OUT_OFF_WHATSAPP_RESPONSE_WINDOW_FEATURE_FLAG_KEY
        )
        self.assertEqual(attributes, {"projectUUID": str(project_uuid)})

    @patch("chats.apps.contacts.feature_flags.is_feature_active_for_attributes")
    def test_evaluation_error_keeps_the_feature_off(self, mock_flag):
        mock_flag.side_effect = RuntimeError("growthbook down")
        self.assertFalse(is_out_off_whatsapp_response_window_enabled(uuid4()))
