from django.test import TestCase
from django.db import transaction

from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.msgs.usecases.set_msg_external_id import SetMsgExternalIdUseCase
from chats.apps.rooms.models import Room


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