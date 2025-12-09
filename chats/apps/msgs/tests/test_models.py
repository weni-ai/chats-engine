import json
from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.msgs.models import Message, MessageMedia, AutomaticMessage
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


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

    def test_message_without_automatic_message(self):
        msg = Message.objects.create(room=self.room)
        self.assertFalse(msg.is_automatic_message)

    def test_message_with_automatic_message(self):
        msg = Message.objects.create(room=self.room)
        AutomaticMessage.objects.create(message=msg, room=self.room)
        self.assertTrue(msg.is_automatic_message)


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


class TestMessageNotifyRoom(TestCase):
    """Test Message.notify_room callback functionality with retries and logging"""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00:00",
            work_end="18:00:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            callback_url="https://example.com/webhook", queue=self.queue
        )
        self.message = Message.objects.create(room=self.room, text="Test message")

    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_notify_room_success_with_default_settings(
        self, mock_get_session, mock_logger, mock_base_notification
    ):
        """Test successful callback with default retry settings"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        mock_get_session.assert_called_once()
        call_args = mock_get_session.call_args[1]

        self.assertEqual(call_args["retries"], 5)
        self.assertEqual(call_args["method_whitelist"], ["POST"])

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        self.assertEqual(call_args[0][0], "https://example.com/webhook")

        mock_logger.error.assert_not_called()

        mock_base_notification.assert_called_once()

    @override_settings(
        CALLBACK_RETRY_COUNT=10,
        CALLBACK_RETRY_BACKOFF_FACTOR=0.5,
        CALLBACK_RETRYABLE_STATUS_CODES=[408, 429, 500, 502, 503, 504],
        CALLBACK_TIMEOUT_SECONDS=30,
    )
    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_notify_room_with_custom_settings(
        self, mock_get_session, mock_logger, mock_base_notification
    ):
        """Test callback with custom retry settings from environment"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        mock_get_session.assert_called_once_with(
            retries=10,
            backoff_factor=0.5,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            method_whitelist=["POST"],
        )

        call_args = mock_session.post.call_args
        self.assertEqual(call_args[1]["timeout"], 30)

    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_notify_room_connection_error(
        self, mock_get_session, mock_logger, mock_base_notification
    ):
        """Test callback handling connection errors with proper logging"""
        mock_session = Mock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("[Message.notify_room] Callback failed", log_message)
        self.assertIn("ConnectionError: Connection failed", log_message)
        self.assertIn(f"Message ID: {self.message.pk}", log_message)

    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_notify_room_timeout_error(
        self, mock_get_session, mock_logger, mock_base_notification
    ):
        """Test callback handling timeout errors"""
        mock_session = Mock()
        mock_session.post.side_effect = requests.exceptions.Timeout("Request timeout")
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("Timeout: Request timeout", log_message)

    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_notify_room_http_error_500(
        self, mock_get_session, mock_logger, mock_base_notification
    ):
        """Test callback handling HTTP 500 error (retryable)"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {"Content-Type": "text/plain"}
        # Não precisa mais do raise_for_status pois está comentado

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        # O erro não será logado porque raise_for_status está comentado
        # Então verificamos que a notificação base foi chamada
        mock_base_notification.assert_called_once()

    @patch("chats.apps.rooms.models.Room.base_notification")
    def test_notify_room_without_callback(self, mock_base_notification):
        """Test notify_room when callback=False doesn't make HTTP request"""
        with patch(
            "chats.apps.msgs.models.get_request_session_with_retries"
        ) as mock_get_session:
            self.message.notify_room(action="create", callback=False)

            mock_get_session.assert_not_called()
            mock_base_notification.assert_called_once()

    @patch("chats.apps.rooms.models.Room.base_notification")
    def test_notify_room_without_callback_url(self, mock_base_notification):
        """Test notify_room when room has no callback_url"""
        self.room.callback_url = None
        self.room.save()

        with patch(
            "chats.apps.msgs.models.get_request_session_with_retries"
        ) as mock_get_session:
            self.message.notify_room(action="create", callback=True)

            mock_get_session.assert_not_called()
            mock_base_notification.assert_called_once()


class TestMessageMediaCallback(TestCase):
    """Test MessageMedia.callback functionality with retries and logging"""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00:00",
            work_end="18:00:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            callback_url="https://example.com/webhook", queue=self.queue
        )
        self.message = Message.objects.create(room=self.room, text="Test message")
        self.media = MessageMedia.objects.create(
            message=self.message,
            content_type="image/jpeg",
            media_url="https://example.com/image.jpg",
        )

    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_callback_success(self, mock_get_session, mock_logger):
        """Test successful MessageMedia callback"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        self.media.callback()

        actual_call = mock_get_session.call_args
        self.assertEqual(actual_call[1]["retries"], 5)
        self.assertEqual(actual_call[1]["method_whitelist"], ["POST"])

        call_args = mock_session.post.call_args
        post_data = json.loads(call_args[1]["data"])
        self.assertEqual(post_data["content"]["text"], "")
        self.assertEqual(post_data["type"], "msg.create")

        mock_logger.error.assert_not_called()

    @patch("chats.apps.msgs.models.logger")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_callback_error_logging(self, mock_get_session, mock_logger):
        """Test MessageMedia callback error logging"""
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Generic error")
        mock_get_session.return_value = mock_session

        self.media.callback()

        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("[MessageMedia.callback] Callback failed", log_message)
        self.assertIn(f"MessageMedia ID: {self.media.pk}", log_message)
        self.assertIn("Exception: Generic error", log_message)

    @patch("chats.apps.rooms.models.Room.base_notification")
    def test_notify_room_delegation(self, mock_base_notification):
        """Test MessageMedia.notify_room delegates to Message"""
        with patch.object(self.message, "notify_room") as mock_notify:
            self.media.notify_room(action="update", callback=True)

            mock_notify.assert_called_once_with("update", True)


class TestRetryConfiguration(TestCase):
    """Test retry configuration"""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00:00",
            work_end="18:00:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            callback_url="https://example.com/webhook", queue=self.queue
        )
        self.message = Message.objects.create(room=self.room, text="Test")

    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_retry_configuration_includes_503(
        self, mock_get_session, mock_base_notification
    ):
        """Test that 503 is included in retry configuration"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        call_args = mock_get_session.call_args[1]
        self.assertIn(503, call_args["status_forcelist"])
        self.assertEqual(call_args["retries"], 5)

    @patch("chats.apps.rooms.models.Room.base_notification")
    @patch("chats.apps.msgs.models.get_request_session_with_retries")
    def test_no_retry_on_404_configuration(
        self, mock_get_session, mock_base_notification
    ):
        """Test that 404 is NOT included in retry configuration"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        self.message.notify_room(action="create", callback=True)

        call_args = mock_get_session.call_args[1]
        self.assertNotIn(404, call_args["status_forcelist"])


class TestMessageMediaUploadTo(TestCase):
    """Test MessageMedia upload_to functionality for unique file names"""

    def setUp(self):
        self.room = Room.objects.create()
        self.message = Message.objects.create(room=self.room, text="Test message")

    def test_upload_to_generates_unique_filenames(self):
        """Test that upload_to generates unique filenames using UUID"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from chats.apps.msgs.models import message_media_upload_to

        # Create two media objects with the same original filename
        file1 = SimpleUploadedFile("test_image.png", b"file_content_1", content_type="image/png")
        file2 = SimpleUploadedFile("test_image.png", b"file_content_2", content_type="image/png")

        media1 = MessageMedia.objects.create(
            message=self.message,
            content_type="image/png",
            media_file=file1
        )

        media2 = MessageMedia.objects.create(
            message=self.message,
            content_type="image/png",
            media_file=file2
        )

        # Get the generated file paths
        path1 = media1.media_file.name
        path2 = media2.media_file.name

        # Assert that paths are different despite same original filename
        self.assertNotEqual(path1, path2)

        # Assert that paths contain the UUID
        self.assertIn(str(media1.uuid), path1)
        self.assertIn(str(media2.uuid), path2)

        # Assert that paths have correct format
        self.assertTrue(path1.startswith("messagemedia/"))
        self.assertTrue(path2.startswith("messagemedia/"))
        self.assertTrue(path1.endswith(".png"))
        self.assertTrue(path2.endswith(".png"))

    def test_upload_to_preserves_file_extension(self):
        """Test that upload_to preserves the original file extension"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_cases = [
            ("image.png", "image/png", ".png"),
            ("document.pdf", "application/pdf", ".pdf"),
            ("video.mp4", "video/mp4", ".mp4"),
            ("audio.ogg", "audio/ogg", ".ogg"),
            ("file.JPG", "image/jpeg", ".jpg"),  # Test uppercase to lowercase
        ]

        for filename, content_type, expected_ext in test_cases:
            with self.subTest(filename=filename):
                file = SimpleUploadedFile(filename, b"content", content_type=content_type)
                media = MessageMedia.objects.create(
                    message=self.message,
                    content_type=content_type,
                    media_file=file
                )
                
                path = media.media_file.name
                self.assertTrue(path.endswith(expected_ext.lower()))

    def test_upload_to_function_directly(self):
        """Test the upload_to function directly"""
        from chats.apps.msgs.models import message_media_upload_to
        
        media = MessageMedia.objects.create(
            message=self.message,
            content_type="image/png"
        )
        
        # Test with different filenames
        result1 = message_media_upload_to(media, "test_image.png")
        result2 = message_media_upload_to(media, "another_image.PNG")
        
        # Both should generate the same path (based on same media UUID)
        self.assertEqual(result1, result2)
        
        # Path should contain UUID and lowercase extension
        self.assertEqual(result1, f"messagemedia/{media.uuid}.png")

    def test_same_timestamp_different_files(self):
        """Test that files uploaded at the same time with same name are unique"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.utils import timezone
        
        timestamp = timezone.now()
        
        # Simulate the bug scenario: same filename at nearly same time
        filename = "Tue_25_Nov_2025_162211_GMT.png"
        
        file1 = SimpleUploadedFile(filename, b"content_room_1", content_type="image/png")
        file2 = SimpleUploadedFile(filename, b"content_room_2", content_type="image/png")
        
        # Create messages in different rooms
        room1 = Room.objects.create()
        room2 = Room.objects.create()
        
        message1 = Message.objects.create(room=room1, created_on=timestamp)
        message2 = Message.objects.create(room=room2, created_on=timestamp)
        
        media1 = MessageMedia.objects.create(
            message=message1,
            content_type="image/png",
            media_file=file1,
            created_on=timestamp
        )
        
        media2 = MessageMedia.objects.create(
            message=message2,
            content_type="image/png",
            media_file=file2,
            created_on=timestamp
        )
        
        # Assert files have different paths
        self.assertNotEqual(media1.media_file.name, media2.media_file.name)
        
        # Assert both are accessible
        self.assertTrue(media1.media_file.name)
        self.assertTrue(media2.media_file.name)
        
        # Assert UUIDs are in paths
        self.assertIn(str(media1.uuid), media1.media_file.name)
        self.assertIn(str(media2.uuid), media2.media_file.name)

    def test_upload_to_with_no_extension(self):
        """Test upload_to handles files without extensions"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from chats.apps.msgs.models import message_media_upload_to
        
        file = SimpleUploadedFile("noextension", b"content", content_type="application/octet-stream")
        media = MessageMedia.objects.create(
            message=self.message,
            content_type="application/octet-stream",
            media_file=file
        )
        
        path = media.media_file.name
        # Should still work, just without extension
        self.assertIn(str(media.uuid), path)
        self.assertTrue(path.startswith("messagemedia/"))

    def test_upload_to_with_multiple_dots(self):
        """Test upload_to correctly extracts extension from filenames with multiple dots"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        file = SimpleUploadedFile("my.file.name.tar.gz", b"content", content_type="application/gzip")
        media = MessageMedia.objects.create(
            message=self.message,
            content_type="application/gzip",
            media_file=file
        )
        
        path = media.media_file.name
        # Should use only the last extension
        self.assertTrue(path.endswith(".gz"))
        self.assertIn(str(media.uuid), path)
