from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.projects.consumers.template_type_consumer import (
    TemplateTypeConsumer,
)


class TestTemplateTypeConsumer(TestCase):
    def setUp(self):
        self.mock_channel = Mock()
        self.mock_message = Mock()
        self.mock_message.channel = self.mock_channel
        self.mock_message.delivery_tag = "ttt"
        self.mock_message.headers = {"x-error-count": 0}

    @patch(
        "chats.apps.projects.consumers.template_type_consumer.TemplateTypeCreation"
    )
    def test_consumes_valid_message_and_acks(self, mock_creation_class):
        self.mock_message.body = b'{"uuid": "u-1", "name": "TT"}'

        TemplateTypeConsumer.consume(self.mock_message)

        mock_creation_class.assert_called_once_with(
            config={"uuid": "u-1", "name": "TT"}
        )
        mock_creation_class.return_value.create.assert_called_once()
        self.mock_channel.basic_ack.assert_called_once_with("ttt")

    @patch(
        "chats.apps.projects.consumers.template_type_consumer.TemplateTypeCreation"
    )
    def test_parse_error_is_rejected_by_decorator(self, mock_creation_class):
        self.mock_message.body = b"{bad json"

        TemplateTypeConsumer.consume(self.mock_message)

        mock_creation_class.assert_not_called()
        self.mock_channel.basic_reject.assert_called_once_with(
            "ttt", requeue=False
        )

    @patch(
        "chats.apps.projects.consumers.template_type_consumer.TemplateTypeCreation"
    )
    def test_usecase_exception_is_rejected(self, mock_creation_class):
        self.mock_message.body = b'{"uuid": "u-1"}'
        mock_creation_class.return_value.create.side_effect = Exception("boom")

        TemplateTypeConsumer.consume(self.mock_message)

        self.mock_channel.basic_reject.assert_called_once_with(
            "ttt", requeue=False
        )
        self.mock_channel.basic_ack.assert_not_called()
