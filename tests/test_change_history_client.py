from datetime import time
from unittest import mock
from unittest.mock import MagicMock

from django.test import SimpleTestCase, TransactionTestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.eda_clients.change_history_client import (
    ChangeHistoryMixin,
    PublishChangeHistoryUseCase,
    publish_change_history,
)
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class ChangeHistoryMixinTests(SimpleTestCase):
    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.EventDrivenAPP"
    )
    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.settings"
    )
    def test_publish_change(self, mock_settings, mock_app):
        mock_settings.USE_EDA = True
        mock_settings.CHANGE_HISTORY_EXCHANGE = "change-history.topic"
        mock_settings.DEFAULT_DEAD_LETTER_EXCHANGE = "chats.dlx.topic"

        ChangeHistoryMixin().publish_change({"foo": "bar"})

        mock_app.return_value.backend.basic_publish.assert_called_once_with(
            content={"foo": "bar"},
            exchange="change-history.topic",
            headers={"callback_exchange": "chats.dlx.topic"},
        )

    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.EventDrivenAPP"
    )
    @mock.patch(
        "chats.apps.api.v1.internal.eda_clients.change_history_client.settings"
    )
    def test_skipped_when_eda_disabled(self, mock_settings, mock_app):
        mock_settings.USE_EDA = False
        ChangeHistoryMixin().publish_change({"foo": "bar"})
        mock_app.assert_not_called()


class PublishChangeHistoryUseCaseTests(TransactionTestCase):
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
        self.publisher = MagicMock()
        self.use_case = PublishChangeHistoryUseCase(publisher=self.publisher)

    def test_create(self):
        content = self.use_case.execute(after=self.queue, user=self.user)
        self.assertEqual(
            content,
            {
                "action": "CREATE",
                "model": "queues.queue",
                "object_id": str(self.queue.uuid),
                "user": "manager@test.com",
            },
        )
        self.publisher.publish_change.assert_called_once_with(content)

    def test_update(self):
        after = Queue.objects.get(pk=self.queue.pk)
        after.name = "Updated"
        content = self.use_case.execute(
            before=self.queue, after=after, user=self.user
        )
        self.assertEqual(content["action"], "UPDATE")

    def test_delete(self):
        content = self.use_case.execute(before=self.queue, user=self.user)
        self.assertEqual(content["action"], "DELETE")

    def test_shortcut(self):
        with mock.patch(
            "chats.apps.api.v1.internal.eda_clients.change_history_client"
            ".PublishChangeHistoryUseCase.execute"
        ) as mock_execute:
            publish_change_history(after=self.queue, user=self.user)
            mock_execute.assert_called_once()
