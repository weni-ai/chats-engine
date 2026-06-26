from django.test import TestCase

from chats.apps.api.utils import create_reply_index
from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.msgs.utils import extract_wamid_core
from chats.apps.rooms.models import Room


WAMID_SAMPLE = (
    "wamid.HBgMNTU0MTk4NTY3MDM0FQIAERgSODVEMjRDRkUyREFBRkM3QTExAA=="
)


class CreateReplyIndexTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create()

    def test_noop_when_message_has_no_external_id(self):
        message = Message.objects.create(room=self.room)

        create_reply_index(message)

        self.assertFalse(ChatMessageReplyIndex.objects.exists())

    def test_creates_entry_with_external_id_core_for_wamid(self):
        message = Message.objects.create(room=self.room, external_id=WAMID_SAMPLE)

        create_reply_index(message)

        index = ChatMessageReplyIndex.objects.get(external_id=WAMID_SAMPLE)
        self.assertEqual(index.message_id, message.pk)
        self.assertEqual(index.external_id_core, extract_wamid_core(WAMID_SAMPLE))
        self.assertIsNotNone(index.external_id_core)

    def test_creates_entry_with_null_core_for_non_wamid_id(self):
        # External integrations (non-WhatsApp) ship arbitrary ids; we must
        # still create the index, just without a core.
        message = Message.objects.create(room=self.room, external_id="legacy-123")

        create_reply_index(message)

        index = ChatMessageReplyIndex.objects.get(external_id="legacy-123")
        self.assertEqual(index.message_id, message.pk)
        self.assertIsNone(index.external_id_core)

    def test_updates_existing_entry_and_repopulates_core(self):
        existing_message = Message.objects.create(
            room=self.room, external_id=WAMID_SAMPLE
        )
        # Insert a row missing ``external_id_core`` to simulate legacy data.
        ChatMessageReplyIndex.objects.create(
            external_id=WAMID_SAMPLE,
            message=existing_message,
            external_id_core=None,
        )

        new_message = Message.objects.create(
            room=self.room, external_id=WAMID_SAMPLE
        )
        create_reply_index(new_message)

        self.assertEqual(
            ChatMessageReplyIndex.objects.filter(external_id=WAMID_SAMPLE).count(),
            1,
        )
        index = ChatMessageReplyIndex.objects.get(external_id=WAMID_SAMPLE)
        self.assertEqual(index.message_id, new_message.pk)
        self.assertEqual(index.external_id_core, extract_wamid_core(WAMID_SAMPLE))
