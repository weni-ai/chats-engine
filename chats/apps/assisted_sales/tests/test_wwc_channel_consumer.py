import json
from unittest import mock
from uuid import uuid4

from django.test import SimpleTestCase, override_settings

from chats.apps.assisted_sales.consumers.wwc_channel_consumer import WwcChannelConsumer


@override_settings(CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE="connect.dlx.topic")
class WwcChannelConsumerTests(SimpleTestCase):
    def setUp(self):
        self.channel = mock.Mock()
        self.message = mock.Mock()
        self.message.channel = self.channel
        self.message.delivery_tag = "tag-1"
        self.message.headers = {"x-error-count": 0}

    def _body(self, payload: dict) -> bytes:
        return json.dumps(payload).encode("utf-8")

    @mock.patch(
        "chats.apps.assisted_sales.consumers.wwc_channel_consumer.UpdateCopilotWwcChannelUseCase"
    )
    def test_dispatches_use_case_when_payload_is_complete(self, mock_use_case_cls):
        channel_uuid = str(uuid4())
        project_uuid = str(uuid4())
        self.message.body = self._body(
            {"channel_uuid": channel_uuid, "project_uuid": project_uuid}
        )

        WwcChannelConsumer.consume(self.message)

        mock_use_case_cls.return_value.execute.assert_called_once_with(
            channel_uuid=channel_uuid,
            project_uuid=project_uuid,
            sector_uuid=None,
        )
        self.channel.basic_ack.assert_called_once_with("tag-1")

    @mock.patch(
        "chats.apps.assisted_sales.consumers.wwc_channel_consumer.UpdateCopilotWwcChannelUseCase"
    )
    def test_accepts_camel_case_payload(self, mock_use_case_cls):
        channel_uuid = str(uuid4())
        project_uuid = str(uuid4())
        sector_uuid = str(uuid4())
        self.message.body = self._body(
            {
                "channelUuid": channel_uuid,
                "projectUuid": project_uuid,
                "sectorUuid": sector_uuid,
            }
        )

        WwcChannelConsumer.consume(self.message)

        mock_use_case_cls.return_value.execute.assert_called_once_with(
            channel_uuid=channel_uuid,
            project_uuid=project_uuid,
            sector_uuid=sector_uuid,
        )
        self.channel.basic_ack.assert_called_once_with("tag-1")

    @mock.patch(
        "chats.apps.assisted_sales.consumers.wwc_channel_consumer.UpdateCopilotWwcChannelUseCase"
    )
    def test_skips_when_channel_uuid_is_missing(self, mock_use_case_cls):
        self.message.body = self._body({"project_uuid": str(uuid4())})

        with self.assertLogs(
            "chats.apps.assisted_sales.consumers.wwc_channel_consumer",
            level="WARNING",
        ) as logs:
            WwcChannelConsumer.consume(self.message)

        mock_use_case_cls.assert_not_called()
        self.channel.basic_ack.assert_called_once_with("tag-1")
        self.assertTrue(
            any("missing channel_uuid or project_uuid" in line for line in logs.output)
        )

    @mock.patch(
        "chats.apps.assisted_sales.consumers.wwc_channel_consumer.UpdateCopilotWwcChannelUseCase"
    )
    def test_skips_when_project_uuid_is_missing(self, mock_use_case_cls):
        self.message.body = self._body({"channel_uuid": str(uuid4())})

        with self.assertLogs(
            "chats.apps.assisted_sales.consumers.wwc_channel_consumer",
            level="WARNING",
        ) as logs:
            WwcChannelConsumer.consume(self.message)

        mock_use_case_cls.assert_not_called()
        self.channel.basic_ack.assert_called_once_with("tag-1")
        self.assertTrue(
            any("missing channel_uuid or project_uuid" in line for line in logs.output)
        )

    @mock.patch(
        "chats.apps.assisted_sales.consumers.wwc_channel_consumer.UpdateCopilotWwcChannelUseCase"
    )
    def test_skips_when_body_is_not_a_dict(self, mock_use_case_cls):
        self.message.body = b'["not", "an", "object"]'

        with self.assertLogs(
            "chats.apps.assisted_sales.consumers.wwc_channel_consumer",
            level="WARNING",
        ) as logs:
            WwcChannelConsumer.consume(self.message)

        mock_use_case_cls.assert_not_called()
        self.channel.basic_ack.assert_called_once_with("tag-1")
        self.assertTrue(any("invalid body" in line for line in logs.output))
