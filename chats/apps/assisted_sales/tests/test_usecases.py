from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings

from chats.apps.assisted_sales.exceptions import CopilotConnectError
from chats.apps.assisted_sales.models import CopilotIntegration
from chats.apps.assisted_sales.tasks import (
    enqueue_set_room_copilot_channel,
    set_room_copilot_channel,
)
from chats.apps.assisted_sales.usecases import (
    CheckCopilotCreatePermissionUseCase,
    SetRoomCopilotChannelUseCase,
    user_can_create_copilot,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

AVAILABLE_ROLES = {
    "0": "not set",
    "1": "viewer",
    "2": "contributor",
    "3": "moderator",
    "4": "support",
    "5": "Chat user",
    "6": "marketing",
}


def _authorization(role):
    return {
        "user": "member@example.com",
        "project_authorization": role,
        "available_roles": AVAILABLE_ROLES,
    }


class UserCanCreateCopilotTests(SimpleTestCase):
    def test_moderator_can_create(self):
        self.assertTrue(user_can_create_copilot(_authorization(3)))

    def test_contributor_cannot_create(self):
        self.assertFalse(user_can_create_copilot(_authorization(2)))

    def test_viewer_cannot_create(self):
        self.assertFalse(user_can_create_copilot(_authorization(1)))

    def test_support_cannot_create(self):
        self.assertFalse(user_can_create_copilot(_authorization(4)))

    def test_missing_roles_cannot_create(self):
        self.assertFalse(user_can_create_copilot({"project_authorization": 3}))

    def test_invalid_authorization_cannot_create(self):
        self.assertFalse(
            user_can_create_copilot(
                {"project_authorization": "admin", "available_roles": AVAILABLE_ROLES}
            )
        )


class CheckCopilotCreatePermissionUseCaseTests(SimpleTestCase):
    def test_returns_true_when_connect_role_is_moderator(self):
        client = MagicMock()
        client.get_project_authorization.return_value = _authorization(3)

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            project_uuid="project-uuid",
            user_email="member@example.com",
        )

        self.assertTrue(can_create)
        client.get_project_authorization.assert_called_once_with(
            "project-uuid", "member@example.com"
        )

    def test_returns_false_when_connect_role_is_not_moderator(self):
        client = MagicMock()
        client.get_project_authorization.return_value = _authorization(2)

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            project_uuid="project-uuid",
            user_email="member@example.com",
        )

        self.assertFalse(can_create)

    def test_raises_when_connect_fails(self):
        client = MagicMock()
        client.get_project_authorization.side_effect = CopilotConnectError(
            status_code=502, error="Connect unavailable"
        )

        with self.assertRaises(CopilotConnectError):
            CheckCopilotCreatePermissionUseCase(client=client).execute(
                project_uuid="project-uuid",
                user_email="member@example.com",
            )


class SetRoomCopilotChannelUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Live Desk", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.channel_uuid = uuid4()

    def _create_integration(self, *, sector=None, channel_uuid=None, connection=None):
        if connection is None:
            connection = {"channelUuid": str(channel_uuid or self.channel_uuid)}
        return CopilotIntegration.objects.create(
            project=self.project,
            sector=sector,
            copilot_project_uuid=uuid4(),
            name="copilot",
            connection=connection,
        )

    def test_sets_channel_from_project_integration(self):
        self._create_integration()

        SetRoomCopilotChannelUseCase().execute(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertEqual(self.room.channel_uuid, self.channel_uuid)

    def test_prefers_sector_integration_over_project(self):
        self._create_integration()
        sector_channel = uuid4()
        self._create_integration(sector=self.sector, channel_uuid=sector_channel)

        SetRoomCopilotChannelUseCase().execute(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertEqual(self.room.channel_uuid, sector_channel)

    def test_does_nothing_without_integration(self):
        SetRoomCopilotChannelUseCase().execute(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertIsNone(self.room.channel_uuid)

    def test_does_nothing_without_channel_uuid(self):
        self._create_integration(connection={"connectOn": "mount"})

        SetRoomCopilotChannelUseCase().execute(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertIsNone(self.room.channel_uuid)

    def test_does_nothing_for_unknown_room(self):
        self._create_integration()

        SetRoomCopilotChannelUseCase().execute(str(uuid4()))

        self.room.refresh_from_db()
        self.assertIsNone(self.room.channel_uuid)

    def test_updates_closed_room_without_save(self):
        self._create_integration()
        self.room.is_active = False
        self.room.save()

        SetRoomCopilotChannelUseCase().execute(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertEqual(self.room.channel_uuid, self.channel_uuid)

    @override_settings(USE_CELERY=False)
    def test_close_sets_channel_inline_when_celery_is_disabled(self):
        self._create_integration()

        self.room.close()

        self.room.refresh_from_db()
        self.assertFalse(self.room.is_active)
        self.assertEqual(self.room.channel_uuid, self.channel_uuid)

    @override_settings(USE_CELERY=True)
    @patch("chats.apps.assisted_sales.tasks.set_room_copilot_channel.delay")
    def test_close_enqueues_task_when_celery_is_enabled(self, mock_delay):
        self._create_integration()

        with self.captureOnCommitCallbacks(execute=True):
            self.room.close()

        mock_delay.assert_called_once_with(str(self.room.pk))
        self.room.refresh_from_db()
        self.assertIsNone(self.room.channel_uuid)

    def test_task_sets_channel_uuid(self):
        self._create_integration()

        set_room_copilot_channel(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertEqual(self.room.channel_uuid, self.channel_uuid)

    @override_settings(USE_CELERY=False)
    def test_enqueue_runs_inline_when_celery_is_disabled(self):
        self._create_integration()

        enqueue_set_room_copilot_channel(str(self.room.pk))

        self.room.refresh_from_db()
        self.assertEqual(self.room.channel_uuid, self.channel_uuid)
