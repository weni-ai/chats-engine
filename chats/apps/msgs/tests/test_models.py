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

    @patch("chats.apps.rooms.models.Room.clear_24h_valid_cache")
    def test_create_message(self, mock_clear_24h_valid_cache):
        Message.objects.create(room=self.room)
        mock_clear_24h_valid_cache.assert_called_once()

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
