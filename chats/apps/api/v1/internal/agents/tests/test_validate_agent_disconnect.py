import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from chats.apps.api.v1.internal.agents.utils import validate_agent_disconnect
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus, CustomStatusType


User = get_user_model()


class ValidateAgentDisconnectTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Disconnect Project")
        self.admin = User.objects.create_user(email="admin@test.com", password="x")
        self.agent = User.objects.create_user(email="agent@test.com", password="x")
        self.admin_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )

    def test_raises_when_required_fields_are_missing(self):
        with self.assertRaises(NotFound):
            validate_agent_disconnect(self.admin, "", self.agent.email)
        with self.assertRaises(NotFound):
            validate_agent_disconnect(self.admin, str(self.project.uuid), "")

    def test_raises_when_project_does_not_exist(self):
        with self.assertRaises(NotFound) as context:
            validate_agent_disconnect(
                self.admin, str(uuid.uuid4()), self.agent.email
            )

        self.assertEqual(str(context.exception.detail), "Project not found")

    def test_raises_when_agent_does_not_exist(self):
        with self.assertRaises(NotFound) as context:
            validate_agent_disconnect(
                self.admin, str(self.project.uuid), "missing@test.com"
            )

        self.assertEqual(str(context.exception.detail), "Agent not found")

    def test_raises_when_requester_has_no_project_permission(self):
        outsider = User.objects.create_user(email="outsider@test.com", password="x")

        with self.assertRaises(PermissionDenied) as context:
            validate_agent_disconnect(
                outsider, str(self.project.uuid), self.agent.email
            )

        self.assertEqual(str(context.exception.detail), "Not allowed on this project")

    def test_raises_when_requester_is_not_admin(self):
        attendant = User.objects.create_user(email="att@test.com", password="x")
        ProjectPermission.objects.create(
            project=self.project,
            user=attendant,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        with self.assertRaises(PermissionDenied) as context:
            validate_agent_disconnect(
                attendant, str(self.project.uuid), self.agent.email
            )

        self.assertEqual(str(context.exception.detail), "Not allowed")

    def test_raises_when_target_has_no_project_permission(self):
        orphan = User.objects.create_user(email="orphan@test.com", password="x")

        with self.assertRaises(NotFound) as context:
            validate_agent_disconnect(
                self.admin, str(self.project.uuid), orphan.email
            )

        self.assertEqual(str(context.exception.detail), "Agent permission not found")

    def test_raises_when_agent_already_disconnected_without_active_custom_status(self):
        self.agent_perm.status = ProjectPermission.STATUS_OFFLINE
        self.agent_perm.save(update_fields=["status"])

        with self.assertRaises(ValidationError) as context:
            validate_agent_disconnect(
                self.admin, str(self.project.uuid), self.agent.email
            )

        self.assertEqual(
            context.exception.detail,
            {"detail": "User already disconnected"},
        )

    def test_allows_offline_agent_with_active_custom_status(self):
        self.agent_perm.status = ProjectPermission.STATUS_OFFLINE
        self.agent_perm.save(update_fields=["status"])
        status_type = CustomStatusType.objects.create(
            name="Lunch",
            project=self.project,
        )
        CustomStatus.objects.create(
            user=self.agent,
            status_type=status_type,
            is_active=True,
        )

        project, target_user, target_perm = validate_agent_disconnect(
            self.admin, str(self.project.uuid), self.agent.email
        )

        self.assertEqual(project, self.project)
        self.assertEqual(target_user, self.agent)
        self.assertEqual(target_perm, self.agent_perm)

    def test_happy_path_returns_project_user_and_permission(self):
        project, target_user, target_perm = validate_agent_disconnect(
            self.admin, str(self.project.uuid), self.agent.email
        )

        self.assertEqual(project, self.project)
        self.assertEqual(target_user, self.agent)
        self.assertEqual(target_perm, self.agent_perm)
