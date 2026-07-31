from unittest.mock import patch

from celery.exceptions import Retry
from django.test import TestCase, override_settings

from chats.apps.msgs.tasks import process_message_status


@override_settings(MESSAGE_STATUS_MAX_RETRIES=3, MESSAGE_STATUS_RETRY_DELAY=0)
class TestProcessMessageStatus(TestCase):
    @patch("chats.apps.msgs.tasks.update_message_usecase")
    @patch("chats.apps.msgs.tasks.ChatMessageReplyIndex.objects.filter")
    def test_calls_usecase_when_index_exists(self, mock_filter, mock_usecase):
        mock_filter.return_value.exists.return_value = True

        process_message_status.run("msg-1", "delivered")

        mock_usecase.update_status_message.assert_called_once_with(
            "msg-1", "delivered"
        )

    @patch("chats.apps.msgs.tasks.update_message_usecase")
    @patch("chats.apps.msgs.tasks.ChatMessageReplyIndex.objects.filter")
    def test_retries_when_index_missing_and_not_last_retry(
        self, mock_filter, mock_usecase
    ):
        mock_filter.return_value.exists.return_value = False

        with patch.object(
            process_message_status, "retry", side_effect=Retry()
        ) as mock_retry:
            with self.assertRaises(Retry):
                process_message_status.run("msg-2", "delivered")

        mock_retry.assert_called_once()
        mock_usecase.update_status_message.assert_not_called()

    @patch("chats.apps.msgs.tasks.update_message_usecase")
    @patch("chats.apps.msgs.tasks.ChatMessageReplyIndex.objects.filter")
    def test_returns_silently_on_last_retry_when_index_missing(
        self, mock_filter, mock_usecase
    ):
        mock_filter.return_value.exists.return_value = False

        # Push a request context that mimics the final retry.
        process_message_status.push_request(retries=2)
        try:
            with patch.object(
                process_message_status, "retry", side_effect=Retry()
            ) as mock_retry:
                result = process_message_status.run("msg-3", "delivered")
        finally:
            process_message_status.pop_request()

        self.assertIsNone(result)
        mock_retry.assert_not_called()
        mock_usecase.update_status_message.assert_not_called()
