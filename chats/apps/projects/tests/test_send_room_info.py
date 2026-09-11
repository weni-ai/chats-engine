from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from django.test import SimpleTestCase

from chats.apps.projects.usecases.send_room_info import RoomInfoUseCase


def _room(
    *,
    config=None,
    secondary_project=None,
    has_queue=True,
    project_uuid=None,
):
    project_uuid = project_uuid or uuid4()
    sector = SimpleNamespace(secondary_project=secondary_project)
    queue = SimpleNamespace(sector=sector) if has_queue else None
    contact = SimpleNamespace(external_id="ext-1")
    return SimpleNamespace(
        uuid=uuid4(),
        created_on=datetime(2024, 1, 15, tzinfo=timezone.utc),
        contact=contact,
        queue=queue,
        project=SimpleNamespace(uuid=project_uuid, config=config),
    )


class RoomInfoUseCaseTests(SimpleTestCase):
    def setUp(self):
        self.use_case = RoomInfoUseCase()
        self.use_case._rooms_client = MagicMock()

    def test_is_infracommerce_false_without_config(self):
        room = _room(config=None, secondary_project={"uuid": "sec"})
        self.assertFalse(self.use_case._is_infracommerce_with_secondary(room))

    def test_is_infracommerce_false_when_not_principal(self):
        room = _room(config={"its_principal": False}, secondary_project={"uuid": "sec"})
        self.assertFalse(self.use_case._is_infracommerce_with_secondary(room))

    def test_is_infracommerce_false_without_queue(self):
        room = _room(
            config={"its_principal": True},
            secondary_project={"uuid": "sec"},
            has_queue=False,
        )
        self.assertFalse(self.use_case._is_infracommerce_with_secondary(room))

    def test_is_infracommerce_true_with_secondary(self):
        room = _room(
            config={"its_principal": True},
            secondary_project={"uuid": "sec"},
        )
        self.assertTrue(self.use_case._is_infracommerce_with_secondary(room))

    def test_get_project_uuid_returns_principal_when_not_infracommerce(self):
        principal = uuid4()
        room = _room(config=None, project_uuid=principal)
        self.assertEqual(self.use_case._get_project_uuid(room), str(principal))

    def test_get_project_uuid_from_secondary_dict(self):
        room = _room(
            config={"its_principal": True},
            secondary_project={"uuid": "secondary-uuid"},
        )
        self.assertEqual(self.use_case._get_project_uuid(room), "secondary-uuid")

    def test_get_project_uuid_from_secondary_string(self):
        room = _room(
            config={"its_principal": True},
            secondary_project="secondary-as-string",
        )
        self.assertEqual(self.use_case._get_project_uuid(room), "secondary-as-string")

    def test_get_project_uuid_falls_back_when_secondary_is_empty(self):
        principal = uuid4()
        room = _room(
            config={"its_principal": True},
            secondary_project=None,
            project_uuid=principal,
        )
        self.assertEqual(self.use_case._get_project_uuid(room), str(principal))

    def test_get_room_sends_payload_to_client(self):
        room = _room(config=None)
        self.use_case.get_room(room)

        self.use_case._rooms_client.request_room.assert_called_once()
        payload = self.use_case._rooms_client.request_room.call_args.kwargs["content"]
        self.assertEqual(payload["uuid"], str(room.uuid))
        self.assertEqual(payload["external_id"], "ext-1")
        self.assertEqual(payload["project_uuid"], str(room.project.uuid))
        self.assertIn("created_on", payload)
