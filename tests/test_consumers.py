from unittest import mock

from django.test import SimpleTestCase

from chats.apps.msgs.consumers.msg_consumer import MsgConsumer
from chats.apps.projects.consumers.project_consumer import ProjectConsumer
from chats.apps.projects.consumers.sector_consumer import SectorConsumer


class DummyChannel:
    def __init__(self):
        self.acked = []

    def basic_ack(self, tag):
        self.acked.append(tag)


class DummyMessage:
    def __init__(self, body):
        self.body = body
        self.channel = DummyChannel()
        self.delivery_tag = 1


class MsgConsumerTests(SimpleTestCase):
    def setUp(self):
        self.message = DummyMessage(body=b"{}")

    @mock.patch(
        "chats.apps.msgs.consumers.msg_consumer.JSONParser.parse",
        return_value={"chats_uuid": "c-uuid", "message_id": "m-id"},
    )
    @mock.patch("chats.apps.msgs.consumers.msg_consumer.SetMsgExternalIdUseCase")
    def test_msg_consumer_calls_usecase(self, mock_usecase_cls, _):
        # Act
        MsgConsumer.consume(self.message)

        # Assert
        mock_usecase_cls.return_value.execute.assert_called_once_with("c-uuid", "m-id")
        self.assertEqual(self.message.channel.acked, [1])

    @mock.patch(
        "chats.apps.msgs.consumers.msg_consumer.JSONParser.parse", return_value={}
    )
    @mock.patch("chats.apps.msgs.consumers.msg_consumer.SetMsgExternalIdUseCase")
    def test_msg_consumer_skips_when_missing_fields(self, mock_usecase_cls, _):
        # Act
        MsgConsumer.consume(self.message)

        # Assert
        mock_usecase_cls.return_value.execute.assert_not_called()
        self.assertEqual(self.message.channel.acked, [1])


class ProjectConsumerTests(SimpleTestCase):
    def setUp(self):
        self.message = DummyMessage(body=b"{}")

    @mock.patch(
        "chats.apps.projects.consumers.project_consumer.JSONParser.parse",
        return_value={"uuid": "p1"},
    )
    @mock.patch("chats.apps.projects.consumers.project_consumer.ProjectCreationUseCase")
    @mock.patch(
        "chats.apps.projects.consumers.project_consumer.SectorSetupHandlerUseCase"
    )
    def test_project_consumer_triggers_creation(
        self, mock_sector_handler, mock_proj_usecase_cls, _
    ):
        # Act
        ProjectConsumer.consume(self.message)

        # Assert
        # Ensure the creation usecase was instantiated with the mocked sector handler
        mock_proj_usecase_cls.assert_called_once_with(mock_sector_handler.return_value)
        # Ensure execute path acked the message
        self.assertEqual(self.message.channel.acked, [1])


class SectorConsumerTests(SimpleTestCase):
    def setUp(self):
        self.message = DummyMessage(body=b"{}")

    @mock.patch(
        "chats.apps.projects.consumers.sector_consumer.JSONParser.parse",
        return_value={"foo": "bar"},
    )
    @mock.patch("chats.apps.projects.consumers.sector_consumer.SectorCreationUseCase")
    def test_sector_consumer_calls_usecase(self, mock_sector_usecase_cls, _):
        # Act
        SectorConsumer.consume(self.message)

        # Assert
        # create_sector_dto should be called once and integrate_feature once
        inst = mock_sector_usecase_cls.return_value
        inst.create_sector_dto.assert_called_once_with({"foo": "bar"})
        inst.integrate_feature.assert_called_once()
        self.assertEqual(self.message.channel.acked, [1])
