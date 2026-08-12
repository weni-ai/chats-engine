from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from chats.utils.websockets import send_channels_group


class SendChannelsGroupTests(SimpleTestCase):
    @override_settings(WS_MESSAGE_RETRIES=3, WEBSOCKET_RETRY_SLEEP=0)
    @patch("chats.utils.websockets.get_channel_layer")
    @patch("chats.utils.websockets.async_to_sync")
    def test_sends_message_to_channel_group(self, mock_async_to_sync, mock_get_layer):
        channel_layer = MagicMock()
        mock_get_layer.return_value = channel_layer
        group_send = MagicMock()
        mock_async_to_sync.return_value = group_send

        send_channels_group(
            group_name="agent_123",
            call_type="notify",
            content={"uuid": "room-1"},
            action="rooms.update",
        )

        mock_async_to_sync.assert_called_once_with(channel_layer.group_send)
        group_send.assert_called_once_with(
            "agent_123",
            {
                "type": "notify",
                "action": "rooms.update",
                "content": '{"uuid": "room-1"}',
            },
        )

    @override_settings(WS_MESSAGE_RETRIES=2, WEBSOCKET_RETRY_SLEEP=0)
    @patch("chats.utils.websockets.capture_exception")
    @patch("chats.utils.websockets.time.sleep")
    @patch("chats.utils.websockets.get_channel_layer")
    @patch("chats.utils.websockets.async_to_sync")
    def test_retries_and_captures_exception_when_all_attempts_fail(
        self, mock_async_to_sync, mock_get_layer, mock_sleep, mock_capture
    ):
        mock_get_layer.return_value = MagicMock()
        mock_async_to_sync.side_effect = RuntimeError("ws down")

        send_channels_group(
            group_name="agent_123",
            call_type="notify",
            content={"ok": True},
            action="rooms.update",
            retry=2,
        )

        self.assertEqual(mock_async_to_sync.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_capture.assert_called_once()
        self.assertIsInstance(mock_capture.call_args[0][0], RuntimeError)

    @override_settings(WS_MESSAGE_RETRIES=3, WEBSOCKET_RETRY_SLEEP=0)
    @patch("chats.utils.websockets.capture_exception")
    @patch("chats.utils.websockets.time.sleep")
    @patch("chats.utils.websockets.get_channel_layer")
    @patch("chats.utils.websockets.async_to_sync")
    def test_succeeds_on_retry_without_capturing_exception(
        self, mock_async_to_sync, mock_get_layer, mock_sleep, mock_capture
    ):
        mock_get_layer.return_value = MagicMock()
        group_send = MagicMock(side_effect=[RuntimeError("fail once"), None])
        mock_async_to_sync.return_value = group_send

        send_channels_group(
            group_name="agent_123",
            call_type="notify",
            content={"ok": True},
            action="rooms.update",
            retry=2,
        )

        self.assertEqual(group_send.call_count, 2)
        mock_sleep.assert_called_once_with(0)
        mock_capture.assert_not_called()
