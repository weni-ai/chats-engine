from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings

from chats.apps.projects.handle import handle_consumers


class HandleConsumersTests(SimpleTestCase):
    def setUp(self):
        self.channel = Mock()

    @override_settings(DISABLE_OLD_PROJECT_CONSUMER=False)
    def test_old_project_consumer_is_registered_when_flag_is_off(self):
        handle_consumers(self.channel)

        queues = [call.args[0] for call in self.channel.basic_consume.call_args_list]
        self.assertIn("chats.projects", queues)

    @override_settings(DISABLE_OLD_PROJECT_CONSUMER=True)
    def test_old_project_consumer_is_not_registered_when_flag_is_on(self):
        handle_consumers(self.channel)

        queues = [call.args[0] for call in self.channel.basic_consume.call_args_list]
        self.assertNotIn("chats.projects", queues)

    @override_settings(DISABLE_OLD_PROJECT_CONSUMER=True)
    def test_other_queues_are_always_registered(self):
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
