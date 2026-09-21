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
    ListCopilotRoomMessagesUseCase,
    SetRoomCopilotChannelUseCase,
    UpdateCopilotWwcChannelUseCase,
    user_can_create_copilot,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

DEFAULT_ROOMS_LIMIT = 5

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
    @patch(
        "chats.apps.assisted_sales.feature_flags.is_assisted_sales_copilot_enabled",
        return_value=True,
    )
    def test_close_sets_channel_inline_when_celery_is_disabled(self, _mock_flag):
        self._create_integration()

        self.room.close()

        self.room.refresh_from_db()
        self.assertFalse(self.room.is_active)
        self.assertEqual(self.room.channel_uuid, self.channel_uuid)

    @override_settings(USE_CELERY=True)
    @patch("chats.apps.assisted_sales.tasks.set_room_copilot_channel.delay")
    @patch(
        "chats.apps.assisted_sales.feature_flags.is_assisted_sales_copilot_enabled",
        return_value=True,
    )
    def test_close_enqueues_task_when_celery_is_enabled(self, _mock_flag, mock_delay):
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


class UpdateCopilotWwcChannelUseCaseTests(TestCase):
    def setUp(self):
        super().setUp()
        patcher = patch(
            "chats.apps.assisted_sales.usecases.is_assisted_sales_copilot_enabled",
            return_value=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.project = Project.objects.create(name="Live Desk", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        self.channel_uuid = uuid4()

    def _create_integration(self, *, sector=None, connection=None):
        if connection is None:
            connection = {
                "socketUrl": "wss://websocket.weni.ai",
                "channelUuid": "",
                "host": "https://flows.weni.ai",
                "connectOn": "mount",
                "storage": "local",
                "callbackUrl": "",
            }
        return CopilotIntegration.objects.create(
            project=self.project,
            sector=sector,
            copilot_project_uuid=uuid4(),
            name="copilot",
            connection=connection,
        )

    @patch(
        "chats.apps.assisted_sales.usecases.is_assisted_sales_copilot_enabled",
        return_value=False,
    )
    def test_does_not_update_channel_when_feature_flag_is_off(self, _flag):
        integration = self._create_integration()

        result = UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=self.project.uuid,
        )

        integration.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(integration.connection["channelUuid"], "")

    def test_updates_project_integration_channel(self):
        integration = self._create_integration()

        UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=self.project.uuid,
        )

        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], str(self.channel_uuid))
        self.assertEqual(integration.connection["socketUrl"], "wss://websocket.weni.ai")
        self.assertEqual(integration.connection["host"], "https://flows.weni.ai")
        self.assertEqual(integration.connection["connectOn"], "mount")

    def test_updates_integration_by_copilot_project_uuid(self):
        integration = self._create_integration()

        UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=integration.copilot_project_uuid,
            is_live_desk_copilot=True,
        )

        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], str(self.channel_uuid))

    def test_skips_when_not_live_desk_copilot(self):
        integration = self._create_integration()

        result = UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=integration.copilot_project_uuid,
            is_live_desk_copilot=False,
        )

        self.assertIsNone(result)
        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], "")

    def test_updates_sector_integration_only(self):
        project_integration = self._create_integration()
        sector_integration = self._create_integration(sector=self.sector)

        UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=self.project.uuid,
            sector_uuid=self.sector.uuid,
        )

        project_integration.refresh_from_db()
        sector_integration.refresh_from_db()
        self.assertEqual(project_integration.connection["channelUuid"], "")
        self.assertEqual(
            sector_integration.connection["channelUuid"], str(self.channel_uuid)
        )

    def test_does_not_update_sector_integration_without_sector_uuid(self):
        sector_integration = self._create_integration(sector=self.sector)

        UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=self.project.uuid,
        )

        sector_integration.refresh_from_db()
        self.assertEqual(sector_integration.connection["channelUuid"], "")

    def test_does_nothing_without_integration(self):
        result = UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=self.project.uuid,
        )

        self.assertIsNone(result)

    def test_does_nothing_without_channel_uuid(self):
        integration = self._create_integration()

        result = UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=None,
            project_uuid=self.project.uuid,
        )

        self.assertIsNone(result)
        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], "")

    def test_does_nothing_without_project_uuid(self):
        integration = self._create_integration()

        result = UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=None,
        )

        self.assertIsNone(result)
        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], "")

    def test_does_nothing_with_invalid_uuid(self):
        integration = self._create_integration()

        result = UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid="not-a-uuid",
            project_uuid=self.project.uuid,
        )

        self.assertIsNone(result)
        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], "")

    @override_settings(
        WENI_WEBCHAT_HOST="https://flows.weni.ai",
        WENI_WEBCHAT_SOCKET_URL="wss://websocket.weni.ai",
    )
    def test_builds_connection_when_empty(self):
        integration = self._create_integration(connection={})

        UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=self.channel_uuid,
            project_uuid=self.project.uuid,
        )

        integration.refresh_from_db()
        self.assertEqual(integration.connection["channelUuid"], str(self.channel_uuid))
        self.assertEqual(integration.connection["socketUrl"], "wss://websocket.weni.ai")
        self.assertEqual(integration.connection["host"], "https://flows.weni.ai")
        self.assertEqual(integration.connection["connectOn"], "mount")
        self.assertEqual(integration.connection["storage"], "local")
        self.assertEqual(integration.connection["callbackUrl"], "")


class ListCopilotRoomMessagesUseCaseTests(TestCase):
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
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, urn="ext:57619149186@"
        )
        self.copilot_uuid = uuid4()
        CopilotIntegration.objects.create(
            project=self.project,
            copilot_project_uuid=self.copilot_uuid,
            name="copilot",
        )

    def test_proxies_using_copilot_uuid_and_room_uuid_as_contact_urn(self):
        client = MagicMock()
        client.list_internal_messages.return_value = {
            "next": None,
            "previous": None,
            "results": [],
        }

        ListCopilotRoomMessagesUseCase(client=client).execute(
            project=self.project,
            room_uuid=self.room.uuid,
            cursor="next-page",
        )

        client.list_internal_messages.assert_called_once_with(
            project_uuid=str(self.copilot_uuid),
            contact_urn=str(self.room.uuid),
            cursor="next-page",
            limit=None,
        )

    def test_prefers_sector_integration(self):
        sector_copilot = uuid4()
        CopilotIntegration.objects.create(
            project=self.project,
            sector=self.sector,
            copilot_project_uuid=sector_copilot,
            name="sector copilot",
        )
        client = MagicMock()
        client.list_internal_messages.return_value = {
            "next": None,
            "previous": None,
            "results": [],
        }

        ListCopilotRoomMessagesUseCase(client=client).execute(
            project=self.project,
            room_uuid=self.room.uuid,
        )

        client.list_internal_messages.assert_called_once_with(
            project_uuid=str(sector_copilot),
            contact_urn=str(self.room.uuid),
            cursor=None,
            limit=None,
        )

    def test_raises_when_room_does_not_exist(self):
        with self.assertRaises(Room.DoesNotExist):
            ListCopilotRoomMessagesUseCase(client=MagicMock()).execute(
                project=self.project,
                room_uuid=uuid4(),
            )

    def test_raises_when_room_belongs_to_another_project(self):
        other_project = Project.objects.create(name="Other", timezone="UTC")
        with self.assertRaises(Room.DoesNotExist):
            ListCopilotRoomMessagesUseCase(client=MagicMock()).execute(
                project=other_project,
                room_uuid=self.room.uuid,
            )

    def test_raises_when_integration_is_missing(self):
        CopilotIntegration.objects.all().delete()
        with self.assertRaises(CopilotIntegration.DoesNotExist):
            ListCopilotRoomMessagesUseCase(client=MagicMock()).execute(
                project=self.project,
                room_uuid=self.room.uuid,
            )
