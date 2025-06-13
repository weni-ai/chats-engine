from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import APIException

from chats.apps.accounts.models import User
from chats.apps.api.v1.msgs.serializers import (
    BaseMessageSerializer,
    ChatCompletionSerializer,
    MessageAndMediaSerializer,
    MessageMediaSerializer,
    MessageMediaSimpleSerializer,
    MessageSerializer,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message, MessageMedia
from chats.apps.rooms.models import Room


class MessageMediaSimpleSerializerTest(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)  # Using fixture user
        self.room = Room.objects.get(
            pk="8b120093-da6b-4417-8b47-52166564fcb5"
        )  # Using fixture room
        self.message = Message.objects.get(
            pk="05029340-58fa-4e8d-91fb-852149bc8f8c"
        )  # Using fixture message
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="image/jpeg",
            media_file=SimpleUploadedFile(
                "test.jpg", b"file_content", content_type="image/jpeg"
            ),
        )

    def test_get_url(self):
        serializer = MessageMediaSimpleSerializer(self.media)
        self.assertIsNotNone(serializer.data["url"])

    def test_get_sender(self):
        # O campo sender não está disponível no serializer
        serializer = MessageMediaSimpleSerializer(self.media)
        self.assertNotIn("sender", serializer.data)


class MessageMediaSerializerTest(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)  # Using fixture user
        self.room = Room.objects.get(
            pk="8b120093-da6b-4417-8b47-52166564fcb5"
        )  # Using fixture room
        self.message = Message.objects.get(
            pk="05029340-58fa-4e8d-91fb-852149bc8f8c"
        )  # Using fixture message

    @patch("chats.apps.api.v1.msgs.serializers.magic.from_buffer")
    @patch("chats.apps.api.v1.msgs.serializers.AudioSegment")
    def test_create_with_audio_file(self, mock_audio_segment, mock_magic):
        mock_magic.return_value = "audio/mpeg"
        mock_audio_segment.from_file.return_value = MagicMock()
        mock_audio_segment.from_file.return_value.export.return_value = None
        audio_file = SimpleUploadedFile(
            "test.mp3", b"audio_content", content_type="audio/mpeg"
        )
        data = {
            "message": self.message.uuid,
            "media_file": audio_file,
            "content_type": "audio/mpeg",
        }
        serializer = MessageMediaSerializer(data=data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            print("Data being sent:", data)
            print("Message ID:", self.message.uuid)
        self.assertTrue(serializer.is_valid())
        media = serializer.save()
        self.assertEqual(media.content_type, "audio/mpeg")


class BaseMessageSerializerTest(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)  # Using fixture user
        self.room = Room.objects.get(
            pk="8b120093-da6b-4417-8b47-52166564fcb5"
        )  # Using fixture room

    def test_create_message_when_room_is_waiting(self):
        self.room.is_waiting = True
        self.room.save()
        data = {
            "room": self.room,
            "text": "Test message",
            "user_email": self.user.email,
        }
        serializer = BaseMessageSerializer(data=data)
        with self.assertRaises(APIException):
            serializer.is_valid(raise_exception=True)
            serializer.save()


class MessageAndMediaSerializerTest(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)  # Using fixture user
        self.room = Room.objects.get(
            pk="8b120093-da6b-4417-8b47-52166564fcb5"
        )  # Using fixture room

    def test_create_message_with_media(self):
        message_data = {
            "room": self.room.uuid,
            "text": "Test message",
            "user_email": self.user.email,
        }
        media_file = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )
        data = {
            "message": message_data,
            "media_file": media_file,
            "content_type": "image/jpeg",
        }
        serializer = MessageAndMediaSerializer(data=data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            print("Data being sent:", data)
            print("Room ID:", self.room.uuid)
        self.assertTrue(serializer.is_valid())
        media = serializer.save()
        self.assertIsNotNone(media.message)
        self.assertEqual(media.message.text, "Test message")


class MessageSerializerTest(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)  # Using fixture user
        self.room = Room.objects.get(
            pk="8b120093-da6b-4417-8b47-52166564fcb5"
        )  # Using fixture room
        self.message = Message.objects.get(
            pk="05029340-58fa-4e8d-91fb-852149bc8f8c"
        )  # Using fixture message
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="image/jpeg",
            media_file=SimpleUploadedFile(
                "test.jpg", b"file_content", content_type="image/jpeg"
            ),
        )

    def test_get_replied_message(self):
        replied_message = Message.objects.get(
            pk="068342c1-36a6-416c-9863-0e26c70ea886"
        )  # Using fixture message
        ChatMessageReplyIndex.objects.create(
            message=replied_message,
            external_id="test-id",
        )
        self.message.metadata = {"context": {"id": "test-id"}}
        self.message.save()
        serializer = MessageSerializer(self.message)
        replied_data = serializer.data["replied_message"]
        self.assertIsNotNone(replied_data)
        self.assertEqual(replied_data["text"], replied_message.text)

    def test_get_replied_message_with_invalid_metadata(self):
        self.message.metadata = {}
        self.message.save()
        serializer = MessageSerializer(self.message)
        self.assertIsNone(serializer.data["replied_message"])


class ChatCompletionSerializerTest(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)  # Using fixture user
        self.room = Room.objects.get(
            pk="8b120093-da6b-4417-8b47-52166564fcb5"
        )  # Using fixture room
        self.message = Message.objects.get(
            pk="05029340-58fa-4e8d-91fb-852149bc8f8c"
        )  # Using fixture message

    def test_get_role_for_user_message(self):
        serializer = ChatCompletionSerializer(self.message)
        self.assertEqual(serializer.data["role"], "assistant")

    def test_get_role_for_contact_message(self):
        contact = Contact.objects.create(
            name="Test Contact", email="test@example.com", phone="+1234567890"
        )
        self.message.contact = contact
        self.message.save()
        serializer = ChatCompletionSerializer(self.message)
        self.assertEqual(serializer.data["role"], "user")
