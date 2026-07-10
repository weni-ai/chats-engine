from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from chats.apps.projects.usecases.dead_letter_handler import DeadLetterHandler
from chats.apps.projects.usecases.exceptions import (
    InvalidDLQHeaders,
    ReceivedErrorMessage,
)
from chats.apps.projects.usecases.send_room_info import RoomInfoUseCase


class DeadLetterHandlerTests(SimpleTestCase):
    def test_raises_on_error_type(self):
        message = SimpleNamespace(headers={})
        handler = DeadLetterHandler(
            message,
            {
                "error_type": "ValidationError",
                "error_message": "bad",
                "original_message": {"a": 1},
            },
        )
        with self.assertRaises(ReceivedErrorMessage):
            handler.execute()

    def test_raises_without_x_death(self):
        message = SimpleNamespace(headers={})
        with self.assertRaises(InvalidDLQHeaders):
            DeadLetterHandler(message, {}).execute()

    def test_raises_on_reject_reason(self):
        message = SimpleNamespace(headers={"x-death": [{"reason": "rejected", "count": 1}]})
        with self.assertRaises(InvalidDLQHeaders):
            DeadLetterHandler(message, {}).execute()

    def test_raises_on_delivery_limit(self):
        message = SimpleNamespace(
            headers={"x-death": [{"reason": "delivery_limit", "count": 1}]}
        )
        with self.assertRaises(InvalidDLQHeaders):
            DeadLetterHandler(message, {}).execute()

    @override_settings(EDA_REQUEUE_LIMIT=3)
    def test_raises_when_requeue_limit_exceeded(self):
        message = SimpleNamespace(
            headers={"x-death": [{"reason": "expired", "count": 3}]}
        )
        with self.assertRaises(InvalidDLQHeaders):
            DeadLetterHandler(message, {}).execute()

    @override_settings(EDA_REQUEUE_LIMIT=5)
    def test_allows_requeue_under_limit(self):
        message = SimpleNamespace(
            headers={"x-death": [{"reason": "expired", "count": 2}]}
        )
        # Should not raise
        DeadLetterHandler(message, {}).execute()


class RoomInfoUseCaseTests(SimpleTestCase):
    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_get_room_principal_project(self, mock_mixin_cls):
        client = Mock()
        mock_mixin_cls.return_value = client
        usecase = RoomInfoUseCase()

        room = Mock()
        room.uuid = "room-1"
        room.project.uuid = "proj-1"
        room.project.config = {}
        room.contact.external_id = "ext-1"
        room.created_on.isoformat.return_value = "2024-01-01T00:00:00"

        usecase.get_room(room)

        client.request_room.assert_called_once()
        content = client.request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], "proj-1")
        self.assertEqual(content["external_id"], "ext-1")

    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_get_room_infracommerce_secondary_dict(self, mock_mixin_cls):
        mock_mixin_cls.return_value = Mock()
        usecase = RoomInfoUseCase()

        room = Mock()
        room.project.uuid = "principal"
        room.project.config = {"its_principal": True}
        room.queue.sector.secondary_project = {"uuid": "secondary-uuid"}

        self.assertEqual(usecase._get_project_uuid(room), "secondary-uuid")

    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_get_room_infracommerce_secondary_string(self, mock_mixin_cls):
        mock_mixin_cls.return_value = Mock()
        usecase = RoomInfoUseCase()

        room = Mock()
        room.project.uuid = "principal"
        room.project.config = {"its_principal": True}
        room.queue.sector.secondary_project = "secondary-str"

        self.assertEqual(usecase._get_project_uuid(room), "secondary-str")

    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_infracommerce_without_secondary_falls_back(self, mock_mixin_cls):
        mock_mixin_cls.return_value = Mock()
        usecase = RoomInfoUseCase()

        room = Mock()
        room.project.uuid = "principal"
        room.project.config = {"its_principal": True}
        room.queue.sector.secondary_project = None

        self.assertEqual(usecase._get_project_uuid(room), "principal")

    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_not_principal(self, mock_mixin_cls):
        mock_mixin_cls.return_value = Mock()
        usecase = RoomInfoUseCase()

        room = Mock()
        room.project.config = {"its_principal": False}
        self.assertFalse(usecase._is_infracommerce_with_secondary(room))

    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_no_config(self, mock_mixin_cls):
        mock_mixin_cls.return_value = Mock()
        usecase = RoomInfoUseCase()

        room = Mock()
        room.project.config = None
        self.assertFalse(usecase._is_infracommerce_with_secondary(room))

    @patch("chats.apps.projects.usecases.send_room_info.RoomsInfoMixin")
    def test_no_queue(self, mock_mixin_cls):
        mock_mixin_cls.return_value = Mock()
        usecase = RoomInfoUseCase()

        room = Mock()
        room.project.config = {"its_principal": True}
        room.queue = None
        self.assertFalse(usecase._is_infracommerce_with_secondary(room))
