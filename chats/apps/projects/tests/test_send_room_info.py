from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from chats.apps.projects.usecases.send_room_info import RoomInfoUseCase


def _make_room(
    *,
    project_config=None,
    secondary_project=None,
    has_queue=True,
    has_sector=True,
    project_uuid=None,
):
    room = MagicMock()
    room.uuid = uuid4()
    room.created_on = datetime.now(timezone.utc)
    room.contact.external_id = "external-123"

    room.project = MagicMock()
    room.project.uuid = project_uuid or uuid4()
    room.project.config = project_config

    if has_queue:
        room.queue = MagicMock()
        if has_sector:
            room.queue.sector = MagicMock()
            room.queue.sector.secondary_project = secondary_project
        else:
            room.queue.sector = None
    else:
        room.queue = None

    return room


class TestRoomInfoUseCase(TestCase):
    @patch(
        "chats.apps.projects.usecases.send_room_info.RoomsInfoMixin.request_room"
    )
    def test_get_room_publishes_principal_project_uuid_when_no_config(
        self, mock_request_room
    ):
        room = _make_room(project_config=None)
        RoomInfoUseCase().get_room(room)

        content = mock_request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], str(room.project.uuid))
        self.assertEqual(content["external_id"], "external-123")
        self.assertEqual(content["uuid"], str(room.uuid))

    @patch(
        "chats.apps.projects.usecases.send_room_info.RoomsInfoMixin.request_room"
    )
    def test_get_room_uses_principal_when_its_principal_false(
        self, mock_request_room
    ):
        room = _make_room(project_config={"its_principal": False})
        RoomInfoUseCase().get_room(room)
        content = mock_request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], str(room.project.uuid))

    @patch(
        "chats.apps.projects.usecases.send_room_info.RoomsInfoMixin.request_room"
    )
    def test_get_room_uses_secondary_uuid_from_dict(self, mock_request_room):
        secondary_uuid = str(uuid4())
        room = _make_room(
            project_config={"its_principal": True},
            secondary_project={"uuid": secondary_uuid},
        )
        RoomInfoUseCase().get_room(room)
        content = mock_request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], secondary_uuid)

    @patch(
        "chats.apps.projects.usecases.send_room_info.RoomsInfoMixin.request_room"
    )
    def test_get_room_uses_secondary_str(self, mock_request_room):
        secondary_uuid = str(uuid4())
        room = _make_room(
            project_config={"its_principal": True},
            secondary_project=secondary_uuid,
        )
        RoomInfoUseCase().get_room(room)
        content = mock_request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], secondary_uuid)

    @patch(
        "chats.apps.projects.usecases.send_room_info.RoomsInfoMixin.request_room"
    )
    def test_get_room_falls_back_to_principal_when_principal_but_no_queue_sector(
        self, mock_request_room
    ):
        room = _make_room(
            project_config={"its_principal": True},
            has_queue=False,
        )
        RoomInfoUseCase().get_room(room)
        content = mock_request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], str(room.project.uuid))

    @patch(
        "chats.apps.projects.usecases.send_room_info.RoomsInfoMixin.request_room"
    )
    def test_get_room_falls_back_to_principal_when_principal_but_no_secondary(
        self, mock_request_room
    ):
        room = _make_room(
            project_config={"its_principal": True},
            secondary_project=None,
        )
        RoomInfoUseCase().get_room(room)
        content = mock_request_room.call_args.kwargs["content"]
        self.assertEqual(content["project_uuid"], str(room.project.uuid))
