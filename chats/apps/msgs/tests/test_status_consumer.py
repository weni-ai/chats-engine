from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.msgs.consumers.msg_status_consumer import MessageStatusConsumer


class TestMessageStatusConsumer(TestCase):
    def setUp(self):
        self.mock_channel = Mock()
        self.mock_message = Mock()
        self.mock_message.channel = self.mock_channel
        self.mock_message.delivery_tag = "delivery-tag-1"
        self.mock_message.headers = {"x-error-count": 0}

    def _set_body(self, body_bytes):
        self.mock_message.body = body_bytes

    @patch(
        "chats.apps.msgs.consumers.msg_status_consumer.process_message_status"
    )
    def test_acks_and_dispatches_when_valid_body(self, mock_process):
        self._set_body(b'{"message_id": "abc", "status": "DELIVERED"}')

        MessageStatusConsumer.consume(self.mock_message)

        mock_process.delay.assert_called_once_with("abc", "DELIVERED")
        self.mock_channel.basic_ack.assert_called_once_with("delivery-tag-1")

    @patch(
        "chats.apps.msgs.consumers.msg_status_consumer.process_message_status"
    )
    def test_invalid_json_acks_and_does_not_dispatch(self, mock_process):
        self._set_body(b"{not json}")

        MessageStatusConsumer.consume(self.mock_message)

        mock_process.delay.assert_not_called()
        self.mock_channel.basic_ack.assert_called_once_with("delivery-tag-1")

    @patch(
        "chats.apps.msgs.consumers.msg_status_consumer.process_message_status"
    )
    def test_empty_body_acks_and_does_not_dispatch(self, mock_process):
        self._set_body(b"null")

        MessageStatusConsumer.consume(self.mock_message)

        mock_process.delay.assert_not_called()
        self.mock_channel.basic_ack.assert_called_once_with("delivery-tag-1")

    @patch(
        "chats.apps.msgs.consumers.msg_status_consumer.process_message_status"
    )
    def test_missing_required_fields_acks_and_does_not_dispatch(self, mock_process):
        self._set_body(b'{"message_id": "abc"}')

        MessageStatusConsumer.consume(self.mock_message)

        mock_process.delay.assert_not_called()
        self.mock_channel.basic_ack.assert_called_once_with("delivery-tag-1")

    @patch(
        "chats.apps.msgs.consumers.msg_status_consumer.process_message_status"
    )
    def test_celery_failure_is_handled_via_decorator(self, mock_process):
        mock_process.delay.side_effect = Exception("celery error")
        self._set_body(b'{"message_id": "abc", "status": "DELIVERED"}')

        # The pyamqp_call_dlx_when_error decorator should catch and reject.
        MessageStatusConsumer.consume(self.mock_message)

        self.mock_channel.basic_ack.assert_not_called()
        self.mock_channel.basic_reject.assert_called_once_with(
            "delivery-tag-1", requeue=False
        )
