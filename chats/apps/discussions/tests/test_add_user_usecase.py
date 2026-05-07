from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from chats.apps.accounts.models import User
from chats.apps.discussions.models import Discussion, DiscussionUser
from chats.apps.discussions.usecases.add_user_to_discussion import (
    AddUserToDiscussionUseCase,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room


@patch("chats.utils.websockets.send_channels_group")
class AddUserToDiscussionUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="Test Sector",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = self.sector.queues.create(name="Test Queue")

        self.creator_user = User.objects.create(
            email="creator@test.com", first_name="Creator", last_name="User"
        )
        self.agent_user = User.objects.create(
            email="agent@test.com", first_name="Agent", last_name="Smith"
        )
        self.outside_user = User.objects.create(
            email="outside@test.com", first_name="Outside", last_name="Person"
        )

        self.creator_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.creator_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.room = Room.objects.create(
            queue=self.queue, project_uuid=str(self.project.pk)
        )
        self.discussion = Discussion.objects.create(
            subject="Test Discussion",
            created_by=self.creator_user,
            room=self.room,
            queue=self.queue,
            is_queued=True,
        )

        self.usecase = AddUserToDiscussionUseCase()

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_adds_user_and_returns_data(self, _mock_ws):
        result = self.usecase.execute(
            self.discussion, self.agent_user.email, self.creator_user
        )

        self.assertEqual(result["first_name"], "Agent")
        self.assertEqual(result["last_name"], "Smith")
        self.assertTrue(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.agent_perm
            ).exists()
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_creates_feedback_message(self, _mock_ws):
        self.usecase.execute(self.discussion, self.agent_user.email, self.creator_user)

        feedback_msg = self.discussion.messages.filter(user__isnull=True).first()
        self.assertIsNotNone(feedback_msg)
        self.assertIn("Agent", feedback_msg.text)

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_raises_when_user_already_added(self, _mock_ws):
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.agent_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )

        with self.assertRaises(ValidationError) as ctx:
            self.usecase.execute(
                self.discussion, self.agent_user.email, self.creator_user
            )

        self.assertEqual(
            ctx.exception.detail["error"],
            f"User {self.agent_user.email} is already added to this discussion",
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_raises_when_user_email_not_found(self, _mock_ws):
        with self.assertRaises(User.DoesNotExist):
            self.usecase.execute(
                self.discussion, "nonexistent@test.com", self.creator_user
            )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_raises_when_user_has_no_project_permission(self, _mock_ws):
        with self.assertRaises(ValidationError):
            self.usecase.execute(
                self.discussion, self.outside_user.email, self.creator_user
            )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_raises_when_from_user_has_no_project_permission(self, _mock_ws):
        from_user = User.objects.create(email="noperm@test.com", first_name="NoPerm")

        with self.assertRaises(ValidationError):
            self.usecase.execute(self.discussion, self.agent_user.email, from_user)

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_does_not_duplicate_discussion_user(self, _mock_ws):
        self.usecase.execute(self.discussion, self.agent_user.email, self.creator_user)

        self.assertEqual(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.agent_perm
            ).count(),
            1,
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_execute_returns_role_in_response(self, _mock_ws):
        result = self.usecase.execute(
            self.discussion, self.agent_user.email, self.creator_user
        )

        self.assertIn("role", result)
