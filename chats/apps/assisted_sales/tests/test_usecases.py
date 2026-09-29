from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, TestCase, override_settings

from chats.apps.api.utils import create_user_and_token
from chats.apps.assisted_sales.exceptions import (
    CopilotConnectError,
    CopilotFeatureDisabled,
)
from chats.apps.assisted_sales.models import CopilotIntegration, CopilotMessageFeedback
from chats.apps.assisted_sales.tasks import (
    enqueue_set_room_copilot_channel,
    set_room_copilot_channel,
)
from chats.apps.assisted_sales.usecases import (
    CheckCopilotCreatePermissionUseCase,
    GetCopilotMessageFeedbackUseCase,
    ListCopilotRoomMessagesUseCase,
    SetRoomCopilotChannelUseCase,
    SubmitCopilotMessageFeedbackUseCase,
    UpdateCopilotWwcChannelUseCase,
    user_can_create_copilot,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

DEFAULT_ROOMS_LIMIT = 5


def _organization(role, email="member@example.com", other_role=None):
    other_email = "chats@weni.ai"
    return {
        "uuid": "org-uuid",
        "authorization": {
            "user__username": email,
            "user__email": email,
            "role": role,
            "is_admin": role == 3,
        },
        "authorizations": {
            "count": 2,
            "users": [
                {
                    "username": other_email,
                    "first_name": "chats",
                    "last_name": "module",
                    "role": other_role if other_role is not None else 3,
                    "photo_user": None,
                },
                {
                    "username": email,
                    "first_name": "Member",
                    "last_name": "",
                    "role": role,
                    "photo_user": None,
                },
            ],
        },
    }


class UserCanCreateCopilotTests(SimpleTestCase):
    def test_org_admin_can_create(self):
        self.assertTrue(user_can_create_copilot(_organization(3), "member@example.com"))

    def test_contributor_cannot_create(self):
        self.assertFalse(
            user_can_create_copilot(_organization(2), "member@example.com")
        )

    def test_viewer_cannot_create(self):
        self.assertFalse(
            user_can_create_copilot(_organization(1), "member@example.com")
        )

    def test_financial_cannot_create(self):
        self.assertFalse(
            user_can_create_copilot(_organization(4), "member@example.com")
        )

    def test_missing_authorization_cannot_create(self):
        self.assertFalse(user_can_create_copilot({}, "member@example.com"))

    def test_invalid_authorization_cannot_create(self):
        self.assertFalse(
            user_can_create_copilot(
                {
                    "authorization": {
                        "role": "admin",
                        "user__email": "member@example.com",
                    }
                },
                "member@example.com",
            )
        )

    def test_authorization_for_another_user_does_not_grant_permission(self):
        data = _organization(2)
        data["authorization"] = {
            "user__username": "chats@weni.ai",
            "user__email": "chats@weni.ai",
            "role": 3,
            "is_admin": True,
        }
        self.assertFalse(user_can_create_copilot(data, "member@example.com"))

    def test_users_list_grants_permission_when_authorization_is_missing(self):
        data = _organization(3)
        data["authorization"] = {}
        self.assertTrue(user_can_create_copilot(data, "member@example.com"))


class CheckCopilotCreatePermissionUseCaseTests(SimpleTestCase):
    def test_returns_true_when_connect_org_role_is_admin(self):
        client = MagicMock()
        client.get_organization.return_value = _organization(3)

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            org_uuid="org-uuid",
            user_email="member@example.com",
            authorization="Bearer user-token",
        )

        self.assertTrue(can_create)
        client.get_organization.assert_called_once_with("org-uuid", "Bearer user-token")

    def test_returns_false_when_connect_org_role_is_not_admin(self):
        client = MagicMock()
        client.get_organization.return_value = _organization(2)

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            org_uuid="org-uuid",
            user_email="member@example.com",
            authorization="Bearer user-token",
        )

        self.assertFalse(can_create)

    def test_returns_false_when_org_uuid_is_missing(self):
        client = MagicMock()

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            org_uuid="",
            user_email="member@example.com",
            authorization="Bearer user-token",
        )

        self.assertFalse(can_create)
        client.get_organization.assert_not_called()

    def test_raises_when_connect_fails(self):
        client = MagicMock()
        client.get_organization.side_effect = CopilotConnectError(
            status_code=502, error="Connect unavailable"
        )

        with self.assertRaises(CopilotConnectError):
            CheckCopilotCreatePermissionUseCase(client=client).execute(
                org_uuid="org-uuid",
                user_email="member@example.com",
                authorization="Bearer user-token",
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


class CopilotMessageFeedbackUseCaseTests(TestCase):
    def setUp(self):
        patcher = patch(
            "chats.apps.assisted_sales.usecases.is_assisted_sales_copilot_enabled",
            return_value=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.user, _ = create_user_and_token("edu")
        self.project = Project.objects.create(name="Live Desk", timezone="UTC")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            urn="ext:57619149186@",
            user=self.user,
        )

    def test_submit_creates_feedback(self):
        feedback, created = SubmitCopilotMessageFeedbackUseCase().execute(
            user=self.user,
            room_uuid=self.room.uuid,
            message_id="msg-1",
            liked=True,
        )

        self.assertTrue(created)
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.room, self.room)
        self.assertEqual(feedback.message_id, "msg-1")
        self.assertTrue(feedback.liked)

    def test_submit_updates_existing_feedback(self):
        SubmitCopilotMessageFeedbackUseCase().execute(
            user=self.user,
            room_uuid=self.room.uuid,
            message_id="msg-1",
            liked=True,
        )

        feedback, created = SubmitCopilotMessageFeedbackUseCase().execute(
            user=self.user,
            room_uuid=self.room.uuid,
            message_id="msg-1",
            liked=False,
            text="Needs work",
            tags=["incorrect_answer"],
        )

        self.assertFalse(created)
        self.assertFalse(feedback.liked)
        self.assertEqual(feedback.text, "Needs work")
        self.assertEqual(feedback.tags, ["incorrect_answer"])
        self.assertEqual(CopilotMessageFeedback.objects.count(), 1)

    def test_submit_raises_when_user_is_not_the_room_agent(self):
        other_user, _ = create_user_and_token("other")
        ProjectPermission.objects.create(
            project=self.project,
            user=other_user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        with self.assertRaises(PermissionDenied):
            SubmitCopilotMessageFeedbackUseCase().execute(
                user=other_user,
                room_uuid=self.room.uuid,
                message_id="msg-1",
                liked=True,
            )

    def test_submit_raises_when_room_does_not_exist(self):
        with self.assertRaises(Room.DoesNotExist):
            SubmitCopilotMessageFeedbackUseCase().execute(
                user=self.user,
                room_uuid=uuid4(),
                message_id="msg-1",
                liked=True,
            )

    def test_submit_raises_when_feature_flag_is_disabled(self):
        with patch(
            "chats.apps.assisted_sales.usecases.is_assisted_sales_copilot_enabled",
            return_value=False,
        ):
            with self.assertRaises(CopilotFeatureDisabled):
                SubmitCopilotMessageFeedbackUseCase().execute(
                    user=self.user,
                    room_uuid=self.room.uuid,
                    message_id="msg-1",
                    liked=True,
                )

    def test_get_returns_feedback_by_message_id(self):
        created = CopilotMessageFeedback.objects.create(
            room=self.room,
            user=self.user,
            message_id="msg-1",
            liked=True,
        )

        feedback = GetCopilotMessageFeedbackUseCase().execute(
            user=self.user,
            room_uuid=self.room.uuid,
            message_id="msg-1",
        )

        self.assertEqual(feedback.uuid, created.uuid)

    def test_get_raises_when_feedback_does_not_exist(self):
        with self.assertRaises(CopilotMessageFeedback.DoesNotExist):
            GetCopilotMessageFeedbackUseCase().execute(
                user=self.user,
                room_uuid=self.room.uuid,
                message_id="missing",
            )

    def test_list_returns_only_current_user_feedbacks(self):
        other_user, _ = create_user_and_token("other-list")
        mine = CopilotMessageFeedback.objects.create(
            room=self.room,
            user=self.user,
            message_id="msg-1",
            liked=True,
        )
        CopilotMessageFeedback.objects.create(
            room=self.room,
            user=other_user,
            message_id="msg-1",
            liked=False,
            text="Other",
        )

        results = list(
            GetCopilotMessageFeedbackUseCase().execute(
                user=self.user,
                room_uuid=self.room.uuid,
            )
        )

        self.assertEqual(results, [mine])
