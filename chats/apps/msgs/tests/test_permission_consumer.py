from unittest import mock

from django.test import TestCase

from chats.apps.projects.consumers.permission_consumer import ProjectPermissionConsumer


class TestProjectPermissionConsumer(TestCase):
    def setUp(self):
        self.mock_channel = mock.Mock()
        self.mock_message = mock.Mock()
        self.mock_message.channel = self.mock_channel
        self.mock_message.delivery_tag = "test_delivery_tag"
        self.mock_message.body = (
            b'{"project": "test_project", "user": "test_user", "role": "admin"}'
        )

    @mock.patch(
        "chats.apps.projects.consumers.permission_consumer.ProjectPermissionCreationUseCase"
    )
    def test_consume_create_action(self, mock_use_case):
        """
        Tests message consumption with 'create' action
        """
        mock_instance = mock.Mock()
        mock_use_case.return_value = mock_instance

        self.mock_message.body = (
            b'{"project": "test_project", "user": "test_user", '
            b'"role": "admin", "action": "create"}'
        )

        ProjectPermissionConsumer.consume(self.mock_message)

        mock_use_case.assert_called_once()
        mock_instance.create_permission.assert_called_once()
        self.mock_channel.basic_ack.assert_called_once_with("test_delivery_tag")

    @mock.patch(
        "chats.apps.projects.consumers.permission_consumer.ProjectPermissionCreationUseCase"
    )
    def test_consume_update_action(self, mock_use_case):
        """
        Tests message consumption with 'update' action
        """
        mock_instance = mock.Mock()
        mock_use_case.return_value = mock_instance

        self.mock_message.body = (
            b'{"project": "test_project", "user": "test_user", '
            b'"role": "admin", "action": "update"}'
        )

        ProjectPermissionConsumer.consume(self.mock_message)

        mock_use_case.assert_called_once()
        mock_instance.create_permission.assert_called_once()
        self.mock_channel.basic_ack.assert_called_once_with("test_delivery_tag")

    @mock.patch(
        "chats.apps.projects.consumers.permission_consumer.ProjectPermissionCreationUseCase"
    )
    def test_consume_delete_action(self, mock_use_case):
        """
        Tests message consumption with 'delete' action
        """
        mock_instance = mock.Mock()
        mock_use_case.return_value = mock_instance

        self.mock_message.body = (
            b'{"project": "test_project", "user": "test_user", '
            b'"role": "admin", "action": "delete"}'
        )

        ProjectPermissionConsumer.consume(self.mock_message)

        mock_use_case.assert_called_once()
        mock_instance.delete_permission.assert_called_once()
        self.mock_channel.basic_ack.assert_called_once_with("test_delivery_tag")

    @mock.patch(
        "chats.apps.projects.consumers.permission_consumer.ProjectPermissionCreationUseCase"
    )
    def test_consume_invalid_json(self, mock_use_case):
        """
        Tests behavior with invalid JSON
        """
        self.mock_message.body = b"{invalid json}"

        ProjectPermissionConsumer.consume(self.mock_message)

        mock_use_case.assert_not_called()
        self.mock_channel.basic_reject.assert_called_once_with(
            "test_delivery_tag", requeue=False
        )
        self.mock_channel.basic_ack.assert_not_called()

    @mock.patch(
        "chats.apps.projects.consumers.permission_consumer.ProjectPermissionCreationUseCase"
    )
    def test_consume_missing_required_fields(self, mock_use_case):
        """
        Tests behavior with missing required fields
        """
        self.mock_message.body = b'{"action": "create"}'

        ProjectPermissionConsumer.consume(self.mock_message)

        mock_use_case.assert_called_once()
        self.mock_channel.basic_ack.assert_called_once_with("test_delivery_tag")

    @mock.patch(
        "chats.apps.projects.consumers.permission_consumer.ProjectPermissionCreationUseCase"
    )
    def test_consume_use_case_error(self, mock_use_case):
        """
        Tests behavior when use case raises an exception
        """
        mock_instance = mock.Mock()
        mock_use_case.return_value = mock_instance
        mock_instance.create_permission.side_effect = Exception("Erro no use case")

        self.mock_message.body = (
            b'{"project": "test_project", "user": "test_user", '
            b'"role": "admin", "action": "create"}'
        )

        ProjectPermissionConsumer.consume(self.mock_message)

        mock_use_case.assert_called_once()
        self.mock_channel.basic_reject.assert_called_once_with(
            "test_delivery_tag", requeue=False
        )
        self.mock_channel.basic_ack.assert_not_called()
