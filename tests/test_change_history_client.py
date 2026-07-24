from datetime import time
from unittest import mock

from django.test import TransactionTestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.eda_clients.change_history_client import (
    publish_change_history,
)
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector


@override_settings(AMQ_BROKER_HOST="localhost")
class PublishChangeHistoryTests(TransactionTestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=5,
            work_start=time(hour=9, minute=0),
            work_end=time(hour=18, minute=0),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="manager@test.com")

    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.Notifier"
    )
    def test_create_queue(self, mock_notifier):
        publish_change_history(after=self.queue, user=self.user)

        mock_notifier.notify_change.assert_called_once()
        args = mock_notifier.notify_change.call_args[0]
        self.assertEqual(args[0], str(self.project.uuid))
        self.assertEqual(args[1], "manager@test.com")
        self.assertEqual(args[3].value, "CREATE")
        self.assertEqual(args[4].value, "QUEUE")
        self.assertEqual(args[5].value, "LIVE_DESK")

    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.Notifier"
    )
    def test_update_queue_sends_name_diff(self, mock_notifier):
        after = Queue.objects.get(pk=self.queue.pk)
        after.name = "Renamed"

        publish_change_history(before=self.queue, after=after, user=self.user)

        kwargs = mock_notifier.notify_change.call_args[1]
        self.assertEqual(kwargs["old_value"], "Test Queue")
        self.assertEqual(kwargs["new_value"], "Renamed")
        self.assertEqual(
            mock_notifier.notify_change.call_args[0][3].value, "UPDATE"
        )

    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.Notifier"
    )
    def test_delete_keeps_object_name_after_soft_delete_mutation(
        self, mock_notifier
    ):
        publish_change_history(before=self.queue, user=self.user)

        # Soft delete mutates the in-memory instance after scheduling publish.
        self.queue.name += self.queue.deleted_sufix()
        self.queue.is_deleted = True

        kwargs = mock_notifier.notify_change.call_args[1]
        self.assertEqual(kwargs["object_name"], "Test Queue")
        self.assertEqual(
            mock_notifier.notify_change.call_args[0][3].value, "DELETE"
        )

    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.Notifier"
    )
    def test_add_agent_uses_action_add_and_entity_user(self, mock_notifier):
        permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        auth = QueueAuthorization.objects.create(
            queue=self.queue,
            permission=permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

        publish_change_history(after=auth, user=self.user)

        args = mock_notifier.notify_change.call_args[0]
        self.assertEqual(args[3].value, "ADD")
        self.assertEqual(args[4].value, "USER")

    def test_both_none_raises(self):
        with self.assertRaises(ValueError):
            publish_change_history()

    @override_settings(AMQ_BROKER_HOST="")
    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.Notifier"
    )
    def test_skips_when_amq_host_not_configured(self, mock_notifier):
        publish_change_history(after=self.queue, user=self.user)
        mock_notifier.notify_change.assert_not_called()
