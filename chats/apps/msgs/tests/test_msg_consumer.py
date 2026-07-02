import logging
from unittest import mock

from django.test import TestCase

from chats.apps.msgs.consumers.msg_consumer import MsgConsumer


class MsgConsumerTests(TestCase):
    def setUp(self):
        self.channel = mock.Mock()
        self.message = mock.Mock()
        self.message.channel = self.channel
        self.message.delivery_tag = "tag-1"
        self.message.headers = {"x-error-count": 0}

    @mock.patch(
        "chats.apps.msgs.consumers.msg_consumer.SetMsgExternalIdUseCase"
    )
    def test_dispatches_use_case_when_payload_is_complete(self, mock_use_case_cls):
        self.message.body = (
            b'{"chats_uuid": "abc-123", "message_id": "wamid.HBgX"}'
        )

        MsgConsumer.consume(self.message)

        mock_use_case_cls.return_value.execute.assert_called_once_with(
            "abc-123", "wamid.HBgX"
        )
        self.channel.basic_ack.assert_called_once_with("tag-1")

    @mock.patch(
        "chats.apps.msgs.consumers.msg_consumer.SetMsgExternalIdUseCase"
    )
    def test_skips_and_warns_when_chats_uuid_is_missing(self, mock_use_case_cls):
        self.message.body = b'{"message_id": "wamid.HBgX"}'

        with self.assertLogs("chats.apps.msgs.consumers.msg_consumer", level="WARNING") as logs:
            MsgConsumer.consume(self.message)

        mock_use_case_cls.assert_not_called()
        self.channel.basic_ack.assert_called_once_with("tag-1")
        self.assertTrue(
            any("missing chats_uuid or message_id" in line for line in logs.output),
            f"expected skip warning, got: {logs.output}",
        )

    @mock.patch(
        "chats.apps.msgs.consumers.msg_consumer.SetMsgExternalIdUseCase"
    )
    def test_skips_and_warns_when_message_id_is_missing(self, mock_use_case_cls):
        self.message.body = b'{"chats_uuid": "abc-123"}'

        with self.assertLogs("chats.apps.msgs.consumers.msg_consumer", level="WARNING") as logs:
            MsgConsumer.consume(self.message)

        mock_use_case_cls.assert_not_called()
        self.channel.basic_ack.assert_called_once_with("tag-1")
        self.assertTrue(
            any("missing chats_uuid or message_id" in line for line in logs.output)
        )

    @mock.patch(
        "chats.apps.msgs.consumers.msg_consumer.SetMsgExternalIdUseCase"
    )
    def test_emits_info_log_for_every_consumed_message(self, mock_use_case_cls):
        self.message.body = (
            b'{"chats_uuid": "abc-123", "message_id": "wamid.HBgX"}'
        )

        with self.assertLogs(
            "chats.apps.msgs.consumers.msg_consumer", level=logging.INFO
        ) as logs:
            MsgConsumer.consume(self.message)

        self.assertTrue(
            any("consuming message" in line for line in logs.output),
            f"expected info log, got: {logs.output}",
        )
