from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.rooms.models import Room


class TestMessageModel(TestCase):
    def setUp(self):
        self.room = Room.objects.create()

    def test_create_message_passing_created_on(self):
        timestamp = timezone.now() - timedelta(days=2)

        msg = Message.objects.create(room=self.room, created_on=timestamp)

        self.assertEqual(msg.created_on.date(), timestamp.date())
        self.assertEqual(msg.created_on.hour, timestamp.hour)
        self.assertEqual(msg.created_on.minute, timestamp.minute)
        self.assertEqual(msg.created_on.second, timestamp.second)

    def test_create_message_without_passing_created_on(self):
        msg = Message.objects.create(room=self.room)

        self.assertEqual(msg.created_on.date(), timezone.now().date())

    def test_create_message_with_context_metadata(self):
        """
        Test creating a message with context metadata.
        Verifies that the metadata is correctly stored and accessible.
        """
        metadata = {
            "context": {
                "from": "usuario_123",
                "id": "c5e502a4-aadf-4dc3-b36f-aad6380e179a",
            }
        }
        msg = Message.objects.create(room=self.room, metadata=metadata)

        self.assertEqual(msg.metadata, metadata)
        self.assertEqual(msg.metadata["context"]["from"], "usuario_123")
        self.assertEqual(
            msg.metadata["context"]["id"], "c5e502a4-aadf-4dc3-b36f-aad6380e179a"
        )

    def test_create_message_without_metadata(self):
        """
        Test creating a message without specifying metadata.
        Verifies that the metadata defaults to an empty dict.
        """
        msg = Message.objects.create(room=self.room)

        self.assertEqual(msg.metadata, {})

    def test_verify_metadata_structure(self):
        """
        Test the structure of the metadata field.
        Ensures that the context dictionary contains the required keys.
        """
        metadata = {
            "context": {
                "from": "usuario_123",
                "id": "c5e502a4-aadf-4dc3-b36f-aad6380e179a",
            }
        }

        msg = Message.objects.create(room=self.room, metadata=metadata)

        self.assertIn("context", msg.metadata)
        self.assertIn("from", msg.metadata["context"])
        self.assertIn("id", msg.metadata["context"])

    def test_message_serialized_data_includes_metadata(self):
        """
        Test if metadata is properly included in the serialized message data.
        Checks if the WebSocket serialization includes the metadata field.
        """
        metadata = {
            "context": {
                "from": "usuario_123",
                "id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
        msg = Message.objects.create(room=self.room, metadata=metadata)

        from chats.apps.msgs.models import ChatMessageReplyIndex

        ChatMessageReplyIndex.objects.create(
            external_id="123e4567-e89b-12d3-a456-426614174000", message=msg
        )

        serialized_data = msg.serialized_ws_data
        self.assertIn("metadata", serialized_data)
        self.assertEqual(serialized_data["metadata"], metadata)

    def test_message_with_empty_context_values(self):
        """
        Test message with empty string values in the context.
        Verifies that empty strings are stored and retrieved correctly.
        """
        metadata = {"context": {"from": "", "id": ""}}
        msg = Message.objects.create(room=self.room, metadata=metadata)

        self.assertEqual(msg.metadata["context"]["from"], "")
        self.assertEqual(msg.metadata["context"]["id"], "")

    def test_message_with_null_metadata_values(self):
        """
        Test message with null values in the metadata.
        Ensures that None values are properly stored and retrieved.
        """
        metadata = {"context": {"from": None, "id": None}}
        msg = Message.objects.create(room=self.room, metadata=metadata)

        self.assertIsNone(msg.metadata["context"]["from"])
        self.assertIsNone(msg.metadata["context"]["id"])


class TestMessageMediaModel(TestCase):
    def setUp(self):
        self.room = Room.objects.create()
        self.msg = Message.objects.create(room=self.room)

    def test_create_message_media_passing_created_on(self):
        timestamp = timezone.now() - timedelta(days=2)

        msg_media = MessageMedia.objects.create(message=self.msg, created_on=timestamp)

        self.assertEqual(msg_media.created_on.date(), timestamp.date())
        self.assertEqual(msg_media.created_on.hour, timestamp.hour)
        self.assertEqual(msg_media.created_on.minute, timestamp.minute)
        self.assertEqual(msg_media.created_on.second, timestamp.second)

    def test_create_message_media_without_passing_created_on(self):
        msg_media = MessageMedia.objects.create(message=self.msg)

        self.assertEqual(msg_media.created_on.date(), timezone.now().date())
