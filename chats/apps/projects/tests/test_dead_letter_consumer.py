from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.projects.consumers.dead_letter_consumer import DeadLetterConsumer


class TestDeadLetterConsumer(TestCase):
    def setUp(self):
        self.mock_channel = Mock()
        self.mock_message = Mock()
        self.mock_message.channel = self.mock_channel
        self.mock_message.delivery_tag = "dt"
        self.mock_message.headers = {"x-first-death-queue": "my.queue"}
        self.mock_message.body = b'{"some": "payload"}'

    @patch(
        "chats.apps.projects.consumers.dead_letter_consumer.basic_publish"
    )
    @patch(
        "chats.apps.projects.consumers.dead_letter_consumer.DeadLetterHandler"
    )
    def test_happy_path_republishes_and_acks(
        self, mock_handler_class, mock_basic_publish
    ):
        mock_handler_class.return_value.execute.return_value = None

        DeadLetterConsumer.consume(self.mock_message)

        mock_handler_class.assert_called_once()
        mock_handler_class.return_value.execute.assert_called_once()
        mock_basic_publish.assert_called_once()
        self.mock_channel.basic_ack.assert_called_once_with("dt")
        self.mock_channel.basic_reject.assert_not_called()

    @patch(
        "chats.apps.projects.consumers.dead_letter_consumer.basic_publish"
    )
    @patch(
        "chats.apps.projects.consumers.dead_letter_consumer.DeadLetterHandler"
    )
    def test_handler_exception_results_in_reject(
        self, mock_handler_class, mock_basic_publish
    ):
        mock_handler_class.return_value.execute.side_effect = Exception("boom")

        DeadLetterConsumer.consume(self.mock_message)

        self.mock_channel.basic_reject.assert_called_once_with("dt", requeue=False)
        self.mock_channel.basic_ack.assert_not_called()
        mock_basic_publish.assert_not_called()
