from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.agents.viewsets import QueueAuthorizationManagementViewset
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization
from chats.apps.rooms.models import Room


def _make_mock_redis():
    return MagicMock(**{"get.return_value": None, "set.return_value": None})


def _make_module_perm():
    content_type = ContentType.objects.get_for_model(User)
    perm, _ = Permission.objects.get_or_create(
        codename="can_communicate_internally",
        content_type=content_type,
    )
    return perm


# ===========================================================================
# ENGAGE-7554 — Individual attendance limit per agent/queue
# New fields: custom_rooms_limit and is_custom_limit_active on QueueAuthorization
# ===========================================================================


class CustomRoomsLimitModelTests(TestCase):
    """Queue.available_agents behaviour when the individual limit is active."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        # sector.rooms_limit = 2 is the baseline limit used across these tests
        self.sector = self.project.sectors.create(
            name="Support", rooms_limit=2, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Queue 1")

        self.agent_user = User.objects.create_user(email="agent@test.com", password="x")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )

    def _create_queue_auth(self, **kwargs):
        return QueueAuthorization.objects.create(
            permission=self.permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
            **kwargs,
        )

    def _fill_active_rooms(self, count):
        """Creates active rooms assigned to the agent in the setUp queue."""
        for _ in range(count):
            contact = Contact.objects.create(name="Contact")
            Room.objects.create(
                contact=contact,
                queue=self.queue,
                user=self.agent_user,
                is_active=True,
            )

    # ------------------------------------------------------------------
    # Case 15
    # ------------------------------------------------------------------

    def test_sector_limit_blocks_agent_when_custom_limit_inactive(self):
        """When is_custom_limit_active=False, sector.rooms_limit is used as the limit."""
        self._create_queue_auth(is_custom_limit_active=False)
        # Agent has reached the sector limit (2 active rooms, limit = 2)
        self._fill_active_rooms(2)

        self.assertNotIn(self.agent_user, self.queue.available_agents)

    # ------------------------------------------------------------------
    # Case 16
    # ------------------------------------------------------------------

    def test_custom_limit_allows_agent_when_sector_limit_exceeded(self):
        """When is_custom_limit_active=True, custom_rooms_limit replaces the sector limit."""
        self._create_queue_auth(is_custom_limit_active=True, custom_rooms_limit=5)
        # 2 active rooms exceed sector.rooms_limit (2) but not custom_rooms_limit (5)
        self._fill_active_rooms(2)

        self.assertIn(self.agent_user, self.queue.available_agents)


class CustomRoomsLimitAPITests(TestCase):
    """API tests for creating and updating the new limit fields on QueueAuthorization."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.module_perm = _make_module_perm()

        self.internal_user = User.objects.create_user(
            email="internal@module.com", password="x"
        )
        self.internal_user.user_permissions.add(self.module_perm)

        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.agent_user = User.objects.create_user(email="agent@test.com", password="x")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = self.project.sectors.create(
            name="Support", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Queue 1")
        self.queue_auth = QueueAuthorization.objects.create(
            permission=self.permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

    def _create(self, mock_redis, data):
        mock_redis.return_value = _make_mock_redis()
        view = QueueAuthorizationManagementViewset.as_view({"post": "create"})
        request = self.factory.post(
            "/internal/queue-authorizations/", data, format="json"
        )
        force_authenticate(request, user=self.internal_user)
        return view(request)

    def _partial_update(self, mock_redis, auth_uuid, data):
        mock_redis.return_value = _make_mock_redis()
        view = QueueAuthorizationManagementViewset.as_view({"patch": "partial_update"})
        request = self.factory.patch(
            f"/internal/queue-authorizations/{auth_uuid}/", data, format="json"
        )
        force_authenticate(request, user=self.internal_user)
        return view(request, uuid=str(auth_uuid))

    # ------------------------------------------------------------------
    # Case 17
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_create_with_custom_limit_fields_saves_and_returns_201(self, mock_redis):
        """Creates a QueueAuthorization with custom_rooms_limit and is_custom_limit_active and returns 201."""
        other_agent = User.objects.create_user(email="other@test.com", password="x")
        other_permission = ProjectPermission.objects.create(
            project=self.project,
            user=other_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        second_queue = self.sector.queues.create(name="Queue 2")

        response = self._create(mock_redis, {
            "queue": str(second_queue.pk),
            "permission": str(other_permission.pk),
            "role": QueueAuthorization.ROLE_AGENT,
            "custom_rooms_limit": 10,
            "is_custom_limit_active": True,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = QueueAuthorization.objects.get(
            queue=second_queue, permission=other_permission
        )
        self.assertEqual(created.custom_rooms_limit, 10)
        self.assertTrue(created.is_custom_limit_active)

    # ------------------------------------------------------------------
    # Case 18
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_partial_update_activates_custom_limit(self, mock_redis):
        """Updates a QueueAuthorization activating is_custom_limit_active and returns 200."""
        response = self._partial_update(mock_redis, self.queue_auth.pk, {
            "is_custom_limit_active": True,
            "custom_rooms_limit": 10,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.queue_auth.refresh_from_db()
        self.assertTrue(self.queue_auth.is_custom_limit_active)
        self.assertEqual(self.queue_auth.custom_rooms_limit, 10)

    # ------------------------------------------------------------------
    # Case 19
    # ------------------------------------------------------------------

    def test_custom_limit_fields_default_to_inactive(self):
        """is_custom_limit_active defaults to False and custom_rooms_limit defaults to None."""
        second_queue = self.sector.queues.create(name="Queue 2")
        auth = QueueAuthorization.objects.create(
            permission=self.permission,
            queue=second_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.assertFalse(auth.is_custom_limit_active)
        self.assertIsNone(auth.custom_rooms_limit)
