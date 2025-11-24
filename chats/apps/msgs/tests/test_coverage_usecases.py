from collections import deque
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    MessageStatusNotifier,
    UpdateStatusMessageUseCase,
)
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


User = get_user_model()


class UpdateStatusMessageUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Msgs Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Support",
            rooms_limit=5,
        )
        self.queue = Queue.objects.create(sector=self.sector, name="Queue")
        self.room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.uuid),
        )
        self.message = Message.objects.create(room=self.room)
        self.reply_index = ChatMessageReplyIndex.objects.create(
            external_id="ext-1",
            message=self.message,
        )
        self.use_case = UpdateStatusMessageUseCase()

    def _create_message_with_reply(self, external_id):
        message = Message.objects.create(room=self.room)
        reply = ChatMessageReplyIndex.objects.create(
            external_id=external_id,
            message=message,
        )
        return message, reply

    def test_mark_delivered_status(self):
        self.use_case.update_status_message(self.reply_index.external_id, "DELIVERED")
        self.use_case._bulk_create()

        self.message.refresh_from_db()
        self.assertEqual(self.message.is_delivered, "delivered")

    def test_mark_read_using_alias(self):
        self.use_case.update_status_message(self.reply_index.external_id, "V")
        self.use_case._bulk_create()

        self.message.refresh_from_db()
        self.assertEqual(self.message.is_read, "read")

    @patch.object(MessageStatusNotifier, "notify_for_message")
    def test_bulk_create_notifies_each_message(self, mock_notify):
        second_message, second_reply = self._create_message_with_reply("ext-2")

        self.use_case.update_status_message(self.reply_index.external_id, "D")
        self.use_case.update_status_message(second_reply.external_id, "READ")
        self.use_case._bulk_create()

        self.message.refresh_from_db()
        second_message.refresh_from_db()

        self.assertEqual(self.message.is_delivered, "delivered")
        self.assertEqual(second_message.is_read, "read")
        self.assertEqual(mock_notify.call_count, 2)

    def test_bulk_create_ignores_invalid_payloads(self):
        invalid_queue = deque([None, {}, {"message_status": "READ"}])
        self.use_case._msgs = invalid_queue

        with patch(
            "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.Message.objects.bulk_update"
        ) as mock_bulk:
            self.use_case._bulk_create()

        self.assertEqual(len(self.use_case._msgs), 0)
        mock_bulk.assert_not_called()

    def test_bulk_create_handles_processing_errors(self):
        second_message, second_reply = self._create_message_with_reply("ext-3")

        with patch(
            "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.ChatMessageReplyIndex.objects.get",
            side_effect=[ValueError("boom"), second_reply],
        ):
            self.use_case.update_status_message(self.reply_index.external_id, "DELIVERED")
            self.use_case.update_status_message(second_reply.external_id, "READ")
            self.use_case._bulk_create()

        self.message.refresh_from_db()
        second_message.refresh_from_db()

        self.assertIsNone(self.message.is_delivered)
        self.assertEqual(second_message.is_read, "read")

    @override_settings(MESSAGE_BULK_SIZE=1)
    def test_update_status_message_triggers_bulk_on_threshold(self):
        use_case = UpdateStatusMessageUseCase()

        with patch.object(use_case, "_bulk_create") as mock_bulk:
            use_case.update_status_message("ext-trigger", "READ")

        mock_bulk.assert_called_once()


class MessageStatusNotifierTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Notify Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Notify",
            rooms_limit=2,
        )
        self.queue = Queue.objects.create(sector=self.sector, name="Notify Queue")
        self.room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.uuid),
        )
        self.user = User.objects.create_user(email="agent@example.com", password="pwd")
        self.room.user = self.user
        self.room.save(update_fields=["user"])
        self.message = Message.objects.create(room=self.room)
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    def test_notify_status_update_sends_channel_event(self):
        with patch(
            "chats.apps.msgs.usecases.UpdateStatusMessageUseCase.send_channels_group"
        ) as mock_send:
            MessageStatusNotifier.notify_status_update(
                self.message.uuid, "delivered", self.permission.pk
            )

        mock_send.assert_called_once_with(
            group_name=f"permission_{self.permission.pk}",
            call_type="notify",
            content={"uuid": str(self.message.uuid), "status": "delivered"},
            action="message.status_update",
        )

    def test_notify_for_message_dispatches_when_permission_exists(self):
        with patch.object(
            MessageStatusNotifier, "notify_status_update"
        ) as mock_notify:
            result = MessageStatusNotifier.notify_for_message(
                self.message, "delivered"
            )

        self.assertTrue(result)
        mock_notify.assert_called_once_with(
            self.message.uuid, "delivered", self.permission.pk
        )

    def test_notify_for_message_returns_false_without_permission(self):
        ProjectPermission.objects.all().delete()

        with patch.object(
            MessageStatusNotifier, "notify_status_update"
        ) as mock_notify:
            result = MessageStatusNotifier.notify_for_message(self.message, "read")

        self.assertFalse(result)
        mock_notify.assert_not_called()

    def test_notify_for_message_returns_false_without_user(self):
        self.room.user = None
        self.room.save(update_fields=["user"])

        result = MessageStatusNotifier.notify_for_message(self.message, "read")

        self.assertFalse(result)

