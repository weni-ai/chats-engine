from unittest import mock

from django.db import transaction
from django.test import TestCase

from chats.apps.msgs.models import ChatMessageReplyIndex, Message, MessageMedia
from chats.apps.msgs.usecases.set_msg_external_id import SetMsgExternalIdUseCase
from chats.apps.rooms.models import Room


WAMID_SAMPLE = (
    "wamid.HBgMNTU0MTk4NTY3MDM0FQIAERgSODVEMjRDRkUyREFBRkM3QTExAA=="
)


class TestSetMsgExternalIdUseCase(TestCase):
    def setUp(self):
        self.room = Room.objects.create()
        self.message = Message.objects.create(room=self.room)
        self.message_media = MessageMedia.objects.create(message=self.message)
        self.use_case = SetMsgExternalIdUseCase()

    def test_set_external_id_for_message(self):
        """
        Tests if external_id is correctly set for a message
        """
        external_id = "123456"
        self.use_case.execute(self.message.uuid, external_id)

        self.message.refresh_from_db()

        self.assertEqual(self.message.external_id, external_id)

    def test_set_external_id_for_message_media(self):
        """
        Tests if external_id is correctly set for a message through MessageMedia
        """
        external_id = "789012"
        self.use_case.execute(self.message_media.uuid, external_id)

        self.message.refresh_from_db()

        self.assertEqual(self.message.external_id, external_id)

    def test_set_external_id_nonexistent_message(self):
        """
        Tests behavior when a non-existent message is passed
        """
        nonexistent_uuid = "00000000-0000-0000-0000-000000000000"
        external_id = "123456"

        self.use_case.execute(nonexistent_uuid, external_id)

    def test_set_external_id_transaction_rollback(self):
        """
        Tests if transaction is rolled back in case of error
        """
        original_external_id = "original"
        self.message.external_id = original_external_id
        self.message.save()

        with self.assertRaises(Exception):
            with transaction.atomic():
                self.use_case.execute(self.message.uuid, "new_id")
                raise Exception("Erro simulado")

        self.message.refresh_from_db()
        self.assertEqual(self.message.external_id, original_external_id)

    def test_creates_reply_index_with_external_id_core_for_wamid(self):
        """
        Setting a WAMID as external_id must produce a ChatMessageReplyIndex
        populated with the corresponding stable core. Regression guard for
        the Bug #2 fix.
        """
        self.use_case.execute(self.message.uuid, WAMID_SAMPLE)

        index = ChatMessageReplyIndex.objects.get(external_id=WAMID_SAMPLE)
        self.assertEqual(index.message_id, self.message.pk)
        self.assertIsNotNone(index.external_id_core)

    def test_unexpected_errors_are_logged_and_reported_without_propagating(self):
        """
        Regression guard for Bug #1: a generic exception inside the use case
        must no longer be silently swallowed, but the consumer should keep
        acking the message instead of routing it to the DLX. Therefore the
        error is captured on Sentry + logger and the call returns normally.
        """
        boom = RuntimeError("boom")
        with mock.patch(
            "chats.apps.msgs.usecases.set_msg_external_id.Message.objects"
        ) as mocked_manager, mock.patch(
            "chats.apps.msgs.usecases.set_msg_external_id.sentry_sdk.capture_exception"
        ) as mocked_capture, self.assertLogs(
            "chats.apps.msgs.usecases.set_msg_external_id", level="ERROR"
        ) as logs:
            mocked_manager.select_for_update.return_value.get.side_effect = boom

            # Must NOT raise.
            self.use_case.execute(self.message.uuid, "any-external-id")

        mocked_capture.assert_called_once_with(boom)
        self.assertTrue(
            any("unexpected error setting external_id" in line for line in logs.output),
            f"expected exception log, got: {logs.output}",
        )
