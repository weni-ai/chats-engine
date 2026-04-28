from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.discussions.models import Discussion, DiscussionUser
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room


@patch("chats.utils.websockets.send_channels_group")
class CreateDiscussionUserViewActionTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="Test Sector",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = self.sector.queues.create(name="Test Queue")

        self.admin_user = User.objects.create(
            email="admin@test.com", first_name="Admin"
        )
        self.creator_user = User.objects.create(
            email="creator@test.com", first_name="Creator"
        )
        self.agent_user = User.objects.create(
            email="agent@test.com", first_name="Agent"
        )
        self.other_agent = User.objects.create(
            email="other@test.com", first_name="Other"
        )
        self.outside_user = User.objects.create(
            email="outside@test.com", first_name="Outside"
        )

        self.admin_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.admin_user,
            role=ProjectPermission.ROLE_ADMIN,
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
        self.other_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.other_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.admin_token = Token.objects.create(user=self.admin_user)
        self.creator_token = Token.objects.create(user=self.creator_user)
        self.agent_token = Token.objects.create(user=self.agent_user)
        self.other_token = Token.objects.create(user=self.other_agent)
        self.outside_token = Token.objects.create(user=self.outside_user)

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

    def _add_agent(self, token, user_email):
        url = (
            reverse("discussion-detail", kwargs={"uuid": self.discussion.uuid})
            + "add_agents/"
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        return self.client.post(url, data={"user_email": user_email}, format="json")

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_creator_can_add_user_to_discussion(self, _mock_ws):
        response = self._add_agent(self.creator_token, self.agent_user.email)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.agent_perm
            ).exists()
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_admin_can_add_user_to_discussion(self, _mock_ws):
        response = self._add_agent(self.admin_token, self.agent_user.email)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.agent_perm
            ).exists()
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_queue_user_can_add_itself_when_discussion_has_less_than_two_users(
        self, _mock_ws
    ):
        self.assertEqual(self.discussion.added_users.count(), 0)

        response = self._add_agent(self.agent_token, self.agent_user.email)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.agent_perm
            ).exists()
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_queue_user_cannot_add_other_users_to_discussion(self, _mock_ws):
        response = self._add_agent(self.agent_token, self.other_agent.email)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.other_perm
            ).exists()
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_added_user_cannot_add_other_users_to_discussion(self, _mock_ws):
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.agent_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.other_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )

        new_user = User.objects.create(email="new@test.com", first_name="New")
        new_perm = ProjectPermission.objects.create(
            project=self.project,
            user=new_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        response = self._add_agent(self.agent_token, new_user.email)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=new_perm
            ).exists()
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_cannot_add_user_already_in_discussion(self, _mock_ws):
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.agent_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )

        response = self._add_agent(self.creator_token, self.agent_user.email)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_add_duplicate_user_returns_already_added_message_and_keeps_single_record(
        self, _mock_ws
    ):
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.agent_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )

        response = self._add_agent(self.admin_token, self.agent_user.email)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["error"],
            f"User {self.agent_user.email} is already added to this discussion",
        )
        self.assertEqual(
            DiscussionUser.objects.filter(
                discussion=self.discussion, permission=self.agent_perm
            ).count(),
            1,
        )

    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_outside_project_user_cannot_add_agents(self, _mock_ws):
        response = self._add_agent(self.outside_token, self.agent_user.email)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@patch("chats.utils.websockets.send_channels_group")
class ListDiscussionUserViewActionTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="Test Sector",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = self.sector.queues.create(name="Test Queue")

        self.admin_user = User.objects.create(
            email="admin@test.com", first_name="Admin"
        )
        self.creator_user = User.objects.create(
            email="creator@test.com", first_name="Creator"
        )
        self.agent_user = User.objects.create(
            email="agent@test.com", first_name="Agent"
        )
        self.other_agent = User.objects.create(
            email="other@test.com", first_name="Other"
        )
        self.outside_user = User.objects.create(
            email="outside@test.com", first_name="Outside"
        )

        self.admin_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.admin_user,
            role=ProjectPermission.ROLE_ADMIN,
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
        self.other_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.other_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.admin_token = Token.objects.create(user=self.admin_user)
        self.creator_token = Token.objects.create(user=self.creator_user)
        self.agent_token = Token.objects.create(user=self.agent_user)
        self.outside_token = Token.objects.create(user=self.outside_user)

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

        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.creator_perm,
            role=DiscussionUser.Role.CREATOR,
        )
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.agent_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )
        DiscussionUser.objects.create(
            discussion=self.discussion,
            permission=self.other_perm,
            role=DiscussionUser.Role.PARTICIPANT,
        )

    def _list_agents(self, token):
        url = (
            reverse("discussion-detail", kwargs={"uuid": self.discussion.uuid})
            + "list_agents/"
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        return self.client.get(url)

    def test_creator_can_list_discussion_users(self, _mock_ws):
        response = self._list_agents(self.creator_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)

    def test_admin_can_list_discussion_users(self, _mock_ws):
        response = self._list_agents(self.admin_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)

    def test_added_user_can_list_discussion_users(self, _mock_ws):
        response = self._list_agents(self.agent_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)

    def test_outside_project_user_cannot_list_discussion_users(self, _mock_ws):
        response = self._list_agents(self.outside_token)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
