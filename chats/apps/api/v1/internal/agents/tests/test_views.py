import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.api.v1.internal.agents.views import AgentDisconnectView
from chats.apps.api.v1.permissions import ProjectBodyIsAdmin
from chats.apps.projects.models import Project, ProjectPermission, CustomStatus
from chats.apps.projects.models.models import AgentDisconnectLog
from chats.apps.projects.usecases.status_service import InServiceStatusService

class ProjectBodyIsAdminPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.User = get_user_model()
        self.user_admin = self.User.objects.create_user(
            email="admin@example.com", password="x"
        )
        self.user_regular = self.User.objects.create_user(
            email="user@example.com", password="x"
        )
        self.project = Project.objects.create(name="P1", timezone="UTC")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user_admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user_regular,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    def _drf_request(self, data, user=None):
        django_request = self.factory.post(
            "/internal/agents/disconnect/", data, format="json"
        )
        # Build a DRF Request to feed has_permission directly
        view = AgentDisconnectView()
        request = view.initialize_request(django_request)
        if user is not None:
            request.user = user
        return request, view

    def test_denies_anonymous(self):
        request, view = self._drf_request({"project_uuid": str(self.project.uuid)})
        perm = ProjectBodyIsAdmin()
        self.assertFalse(perm.has_permission(request, view))

    def test_raises_when_missing_project_uuid(self):
        request, view = self._drf_request({}, user=self.user_admin)
        perm = ProjectBodyIsAdmin()
        with self.assertRaises(ValidationError):
            perm.has_permission(request, view)

    def test_returns_true_for_admin(self):
        request, view = self._drf_request(
            {"project_uuid": str(self.project.uuid)}, user=self.user_admin
        )
        perm = ProjectBodyIsAdmin()
        self.assertTrue(perm.has_permission(request, view))

    def test_returns_false_for_non_admin(self):
        request, view = self._drf_request(
            {"project_uuid": str(self.project.uuid)}, user=self.user_regular
        )
        perm = ProjectBodyIsAdmin()
        self.assertFalse(perm.has_permission(request, view))

    def test_returns_false_for_unknown_project(self):
        request, view = self._drf_request(
            {"project_uuid": str(uuid.uuid4())}, user=self.user_admin
        )
        perm = ProjectBodyIsAdmin()
        self.assertFalse(perm.has_permission(request, view))


@override_settings(USE_CELERY=False)
class AgentDisconnectViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.User = get_user_model()
        self.admin = self.User.objects.create_user(
            email="admin@example.com", password="x"
        )
        self.agent = self.User.objects.create_user(
            email="agent@example.com", password="x"
        )
        self.other = self.User.objects.create_user(
            email="other@example.com", password="x"
        )
        self.project = Project.objects.create(name="P1", timezone="UTC")
        # Permissions
        self.admin_perm = ProjectPermission.objects.create(
            project=self.project, user=self.admin, role=ProjectPermission.ROLE_ADMIN
        )
        self.agent_perm = ProjectPermission.objects.create(
            project=self.project, user=self.agent, role=ProjectPermission.ROLE_ATTENDANT
        )

    def _call_view(self, data, user):
        view = AgentDisconnectView.as_view()
        request = self.factory.post("/internal/agents/disconnect/", data, format="json")
        force_authenticate(request, user=user)
        return view(request)

    @patch(
        "chats.apps.api.v1.internal.agents.views.send_channels_group", return_value=None
    )
    def test_success_admin_disconnects_agent(self, _mock_ws):
        # garantir que não caia no 'User already disconnected'
        self.agent_perm.status = ProjectPermission.STATUS_ONLINE
        self.agent_perm.save(update_fields=["status"])

        with patch("django.db.transaction.on_commit", lambda f: f()):
            response = self._call_view(
                {"project_uuid": str(self.project.uuid), "agent": self.agent.email},
                self.admin,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # target set to OFFLINE
        self.agent_perm.refresh_from_db()
        self.assertEqual(self.agent_perm.status, ProjectPermission.STATUS_OFFLINE)
        # audit log created
        self.assertTrue(
            AgentDisconnectLog.objects.filter(
                project=self.project, agent=self.agent, disconnected_by=self.admin
            ).exists()
        )

    def test_unauthenticated_returns_401(self):
        view = AgentDisconnectView.as_view()
        request = self.factory.post(
            "/internal/agents/disconnect/",
            {"project_uuid": str(self.project.uuid), "agent": self.agent.email},
            format="json",
        )
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_blocks_non_admin_with_403(self):
        response = self._call_view(
            {"project_uuid": str(self.project.uuid), "agent": self.agent.email},
            self.agent,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_project_uuid_returns_400(self):
        response = self._call_view({"agent": self.agent.email}, self.admin)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_uuid", response.data)

    def test_agent_not_found_returns_404(self):
        response = self._call_view(
            {"project_uuid": str(self.project.uuid), "agent": "noone@example.com"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_agent_permission_not_found_returns_404(self):
        response = self._call_view(
            {"project_uuid": str(self.project.uuid), "agent": self.other.email},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("chats.apps.api.v1.internal.agents.views.send_channels_group", return_value=None)
    def test_disconnect_without_custom_status_sets_offline_and_sends_status_close(self, mock_ws):
        # Ensure agent is ONLINE and has no active CustomStatus
        self.agent_perm.status = ProjectPermission.STATUS_ONLINE
        self.agent_perm.save(update_fields=["status"])
        self.assertFalse(
            CustomStatus.objects.filter(user=self.agent, project=self.project, is_active=True).exists()
        )

        with patch("django.db.transaction.on_commit", lambda f: f()):
            resp = self._call_view(
                {"project_uuid": str(self.project.uuid), "agent": self.agent.email},
                self.admin,
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.agent_perm.refresh_from_db()
        self.assertEqual(self.agent_perm.status, ProjectPermission.STATUS_OFFLINE)

        actions = [c.kwargs.get("action") for c in mock_ws.call_args_list]
        self.assertIn("status.close", actions)
        self.assertNotIn("custom_status.close", actions)

    @patch("chats.apps.api.v1.internal.agents.views.send_channels_group", return_value=None)
    def test_disconnect_with_active_custom_status_closes_status_and_sends_custom_status_close(self, mock_ws):
        # Create an active CustomStatus for agent
        status_type = InServiceStatusService.get_or_create_status_type(self.project)
        CustomStatus.objects.create(
            user=self.agent, status_type=status_type, is_active=True, project=self.project, break_time=0
        )
        self.assertTrue(
            CustomStatus.objects.filter(user=self.agent, project=self.project, is_active=True).exists()
        )

        with patch("django.db.transaction.on_commit", lambda f: f()):
            resp = self._call_view(
                {"project_uuid": str(self.project.uuid), "agent": self.agent.email},
                self.admin,
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # CustomStatus must be closed
        self.assertFalse(
            CustomStatus.objects.filter(user=self.agent, project=self.project, is_active=True).exists()
        )
        # Only custom_status.close should be sent in this path
        actions = [c.kwargs.get("action") for c in mock_ws.call_args_list]
        self.assertIn("custom_status.close", actions)
        self.assertNotIn("status.close", actions)

    @patch("chats.apps.api.v1.internal.agents.views.send_channels_group", return_value=None)
    def test_accepts_agent_email_alias(self, mock_ws):
        # ONLINE without CustomStatus -> should go OFFLINE with status.close
        self.agent_perm.status = ProjectPermission.STATUS_ONLINE
        self.agent_perm.save(update_fields=["status"])

        with patch("django.db.transaction.on_commit", lambda f: f()):
            resp = self._call_view(
                {"project_uuid": str(self.project.uuid), "agent_email": self.agent.email},
                self.admin,
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.agent_perm.refresh_from_db()
        self.assertEqual(self.agent_perm.status, ProjectPermission.STATUS_OFFLINE)
        actions = [c.kwargs.get("action") for c in mock_ws.call_args_list]
        self.assertIn("status.close", actions)