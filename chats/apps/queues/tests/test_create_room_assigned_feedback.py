from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from chats.apps.queues.utils import create_room_assigned_from_queue_feedback
from chats.apps.rooms.choices import RoomFeedbackMethods


class CreateRoomAssignedFromQueueFeedbackTests(SimpleTestCase):
    @patch("chats.apps.rooms.views.create_room_feedback_message")
    @patch(
        "chats.apps.queues.utils.create_transfer_json", return_value={"action": "auto"}
    )
    def test_creates_transfer_feedback(self, mock_transfer, mock_feedback):
        room = SimpleNamespace(queue="queue-obj")
        user = SimpleNamespace(email="agent@test.com")

        create_room_assigned_from_queue_feedback(room, user)

        mock_transfer.assert_called_once_with(
            action="auto_assign_from_queue",
            from_=room.queue,
            to=user,
        )
        mock_feedback.assert_called_once_with(
            room,
            {"action": "auto"},
            method=RoomFeedbackMethods.ROOM_TRANSFER,
        )
