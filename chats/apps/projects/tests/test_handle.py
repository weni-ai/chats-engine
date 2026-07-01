from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from chats.apps.projects.handle import handle_consumers


class HandleConsumersTests(SimpleTestCase):
    def setUp(self):
        self.channel = Mock()

    @patch("chats.apps.projects.handle.is_feature_active", return_value=False)
    def test_old_project_consumer_is_registered_when_flag_is_off(self, _):
        handle_consumers(self.channel)

        queues = [call.args[0] for call in self.channel.basic_consume.call_args_list]
        self.assertIn("chats.projects", queues)

    @patch("chats.apps.projects.handle.is_feature_active", return_value=True)
    def test_old_project_consumer_is_not_registered_when_flag_is_on(self, _):
        handle_consumers(self.channel)

        queues = [call.args[0] for call in self.channel.basic_consume.call_args_list]
        self.assertNotIn("chats.projects", queues)

    @patch("chats.apps.projects.handle.is_feature_active", return_value=True)
    def test_other_queues_are_always_registered(self, _):
        handle_consumers(self.channel)

        queues = [call.args[0] for call in self.channel.basic_consume.call_args_list]
        self.assertEqual(
            queues,
            [
                "chats.template-types",
                "chats.update-projects",
                "chats.permissions",
                "chats.integrated-feature",
                "chats.dlq",
            ],
        )
