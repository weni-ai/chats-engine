"""Tests for the MetricGoalAlertConsumer."""

import json
from unittest.mock import patch

from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase, override_settings

from chats.apps.accounts.authentication.channels.middleware import TokenAuthMiddleware
from chats.apps.api.utils import create_user_and_token
from chats.apps.api.websockets.rooms.routing import websocket_urlpatterns
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector, SectorAuthorization


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
)
class MetricGoalAlertConsumerTestCase(TestCase):
    def setUp(self):
        self.application = TokenAuthMiddleware(URLRouter(websocket_urlpatterns))

        self.admin, self.admin_token = create_user_and_token(nickname="goalsadmin")
        self.manager, self.manager_token = create_user_and_token(
            nickname="goalsmanager"
        )
        self.attendant, self.attendant_token = create_user_and_token(
            nickname="goalsatt"
        )
        self.other, self.other_token = create_user_and_token(nickname="goalsother")

        self.project = Project.objects.create(name="WS Goals Project")
        self.other_project = Project.objects.create(name="Other Project")

        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )

        ProjectPermission.objects.create(
            project=self.project,
            user=self.admin,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self.manager_permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.manager,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=self.manager_permission,
            sector=self.sector,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        ProjectPermission.objects.create(
            project=self.project,
            user=self.attendant,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.ff_patch = patch(
            "chats.apps.dashboard.services.metric_goal_alerts.is_feature_active_for_attributes",
            return_value=True,
        )
        self.ff_patch.start()
        self.addCleanup(self.ff_patch.stop)

    def _ws_url(self, project_uuid, token):
        return (
            f"/ws/dashboard/metric-goals?project={project_uuid}&Token={token}"
        )

    async def test_rejects_without_token(self):
        comm = WebsocketCommunicator(
            self.application,
            f"/ws/dashboard/metric-goals?project={self.project.uuid}",
        )
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    async def test_rejects_without_project(self):
        comm = WebsocketCommunicator(
            self.application,
            f"/ws/dashboard/metric-goals?Token={self.admin_token.key}",
        )
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    async def test_rejects_user_without_permission(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.other_token.key),
        )
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    async def test_rejects_attendant_without_dashboard_access(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.attendant_token.key),
        )
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    async def test_accepts_admin(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.admin_token.key),
        )
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.disconnect()

    async def test_accepts_manager_with_sector_authorization(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.manager_token.key),
        )
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.disconnect()

    async def test_receives_broadcast_for_own_project(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.admin_token.key),
        )
        connected, _ = await comm.connect()
        self.assertTrue(connected)

        layer = get_channel_layer()
        await layer.group_send(
            f"metric_goal_alerts:{self.project.uuid}",
            {
                "type": "metric_goal_violated",
                "action": "metric_goal.violated",
                "content": json.dumps({"project_uuid": str(self.project.uuid)}),
            },
        )
        message = await comm.receive_json_from(timeout=2)
        self.assertEqual(message["type"], "metric_goal.violated")
        self.assertEqual(
            message["content"]["project_uuid"], str(self.project.uuid)
        )
        await comm.disconnect()

    async def test_does_not_receive_broadcast_for_other_project(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.admin_token.key),
        )
        connected, _ = await comm.connect()
        self.assertTrue(connected)

        layer = get_channel_layer()
        await layer.group_send(
            f"metric_goal_alerts:{self.other_project.uuid}",
            {
                "type": "metric_goal_violated",
                "action": "metric_goal.violated",
                "content": json.dumps(
                    {"project_uuid": str(self.other_project.uuid)}
                ),
            },
        )
        self.assertTrue(await comm.receive_nothing(timeout=0.5))
        await comm.disconnect()

    async def test_ping_pong(self):
        comm = WebsocketCommunicator(
            self.application,
            self._ws_url(self.project.uuid, self.admin_token.key),
        )
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.send_json_to({"type": "ping"})
        response = await comm.receive_json_from(timeout=2)
        self.assertEqual(response, {"type": "pong"})
        await comm.disconnect()
