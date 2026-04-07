import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.agents.viewsets import (
    AgentQueueAuthorizationViewset,
    QueueAuthorizationManagementViewset,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization


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
# ENGAGE-7558 — GET /internal/agents/{permission_uuid}/
# Endpoint that returns all sectors and queues for a given user
# ===========================================================================


class AgentQueueAuthorizationViewsetTests(TestCase):
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

    def _retrieve(self, mock_redis, permission_uuid=None, user=None):
        mock_redis.return_value = _make_mock_redis()
        target_uuid = permission_uuid or str(self.permission.pk)
        view = AgentQueueAuthorizationViewset.as_view({"get": "retrieve"})
        request = self.factory.get(f"/internal/agents/{target_uuid}/")
        force_authenticate(request, user=user or self.internal_user)
        return view(request, uuid=target_uuid)

    # ------------------------------------------------------------------
    # Case 1
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_returns_all_queue_authorizations_for_valid_user(self, mock_redis):
        """Returns all QueueAuthorizations (queue + sector) for a valid user."""
        response = self._retrieve(mock_redis)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("queue_authorizations", response.data)
        self.assertEqual(len(response.data["queue_authorizations"]), 1)

        auth = response.data["queue_authorizations"][0]
        self.assertEqual(auth["uuid"], str(self.queue_auth.pk))
        self.assertEqual(auth["queue"]["uuid"], str(self.queue.pk))
        self.assertEqual(auth["queue"]["sector"]["uuid"], str(self.sector.pk))

    # ------------------------------------------------------------------
    # Case 2
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_returns_empty_when_user_has_no_queue_authorizations(self, mock_redis):
        """Returns an empty list for a user with no QueueAuthorizations."""
        other_agent = User.objects.create_user(email="other@test.com", password="x")
        permission_without_auth = ProjectPermission.objects.create(
            project=self.project,
            user=other_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        response = self._retrieve(mock_redis, permission_uuid=str(permission_without_auth.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["queue_authorizations"], [])

    # ------------------------------------------------------------------
    # Case 3
    # ------------------------------------------------------------------

    def test_unauthenticated_returns_401(self):
        """Returns 401 when no authentication credentials are provided."""
        view = AgentQueueAuthorizationViewset.as_view({"get": "retrieve"})
        request = self.factory.get(f"/internal/agents/{self.permission.pk}/")
        response = view(request, uuid=str(self.permission.pk))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Case 4
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_without_module_permission_returns_403(self, mock_redis):
        """Returns 403 when user lacks the can_communicate_internally permission."""
        unauthorized_user = User.objects.create_user(email="unauth@test.com", password="x")

        response = self._retrieve(mock_redis, user=unauthorized_user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # Case 5
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_returns_multiple_authorizations_when_agent_has_multiple_queues(self, mock_redis):
        """Returns all authorizations when the agent belongs to more than one queue."""
        second_queue = self.sector.queues.create(name="Queue 2")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=second_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self._retrieve(mock_redis)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["queue_authorizations"]), 2)

    # ------------------------------------------------------------------
    # Case 6
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_nonexistent_permission_uuid_returns_404(self, mock_redis):
        """Returns 404 when the permission UUID does not exist."""
        response = self._retrieve(mock_redis, permission_uuid=str(uuid.uuid4()))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ===========================================================================
# ENGAGE-7557 — CRUD + bulk delete of QueueAuthorization
# ===========================================================================


class QueueAuthorizationManagementViewsetTests(TestCase):
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

    def _list(self, mock_redis, query_string=""):
        mock_redis.return_value = _make_mock_redis()
        view = QueueAuthorizationManagementViewset.as_view({"get": "list"})
        request = self.factory.get(f"/internal/queue-authorizations/{query_string}")
        force_authenticate(request, user=self.internal_user)
        return view(request)

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

    def _destroy(self, mock_redis, auth_uuid):
        mock_redis.return_value = _make_mock_redis()
        view = QueueAuthorizationManagementViewset.as_view({"delete": "destroy"})
        request = self.factory.delete(f"/internal/queue-authorizations/{auth_uuid}/")
        force_authenticate(request, user=self.internal_user)
        return view(request, uuid=str(auth_uuid))

    def _bulk_delete(self, mock_redis, data):
        mock_redis.return_value = _make_mock_redis()
        view = QueueAuthorizationManagementViewset.as_view({"post": "bulk_delete"})
        request = self.factory.post(
            "/internal/queue-authorizations/bulk_delete/", data, format="json"
        )
        force_authenticate(request, user=self.internal_user)
        return view(request)

    # ------------------------------------------------------------------
    # Case 7
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_create_with_valid_data_returns_201(self, mock_redis):
        """Creates a QueueAuthorization with valid data and returns 201."""
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
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            QueueAuthorization.objects.filter(
                queue=second_queue, permission=other_permission
            ).exists()
        )

    # ------------------------------------------------------------------
    # Case 8
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_create_duplicate_returns_400(self, mock_redis):
        """Returns 400 when trying to create a duplicate (same queue + permission)."""
        response = self._create(mock_redis, {
            "queue": str(self.queue.pk),
            "permission": str(self.permission.pk),
            "role": QueueAuthorization.ROLE_AGENT,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Case 9
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_partial_update_role_returns_200(self, mock_redis):
        """Updates the role of an existing authorization and returns 200."""
        response = self._partial_update(mock_redis, self.queue_auth.pk, {
            "role": QueueAuthorization.ROLE_NOT_SETTED,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.queue_auth.refresh_from_db()
        self.assertEqual(self.queue_auth.role, QueueAuthorization.ROLE_NOT_SETTED)

    # ------------------------------------------------------------------
    # Case 10
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_destroy_single_authorization_returns_204(self, mock_redis):
        """Deletes a single authorization and returns 204."""
        response = self._destroy(mock_redis, self.queue_auth.pk)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            QueueAuthorization.objects.filter(pk=self.queue_auth.pk).exists()
        )

    # ------------------------------------------------------------------
    # Case 11
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_bulk_delete_valid_uuids_deletes_all(self, mock_redis):
        """Bulk delete with a list of valid UUIDs removes all of them."""
        second_queue = self.sector.queues.create(name="Queue 2")
        second_auth = QueueAuthorization.objects.create(
            permission=self.permission,
            queue=second_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self._bulk_delete(mock_redis, {
            "uuids": [str(self.queue_auth.pk), str(second_auth.pk)],
        })

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(QueueAuthorization.objects.filter(pk=self.queue_auth.pk).exists())
        self.assertFalse(QueueAuthorization.objects.filter(pk=second_auth.pk).exists())

    # ------------------------------------------------------------------
    # Case 12
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_bulk_delete_with_nonexistent_uuid_returns_400(self, mock_redis):
        """Bulk delete with nonexistent UUIDs returns 400 with a descriptive error."""
        response = self._bulk_delete(mock_redis, {
            "uuids": [str(self.queue_auth.pk), str(uuid.uuid4())],
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uuids", response.data)

    # ------------------------------------------------------------------
    # Case 13
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_bulk_delete_with_empty_list_returns_400(self, mock_redis):
        """Bulk delete with an empty list returns 400."""
        response = self._bulk_delete(mock_redis, {"uuids": []})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Case 14
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_list_filtered_by_permission_returns_only_matching_authorizations(self, mock_redis):
        """Listing filtered by permission returns only the authorizations of that agent."""
        other_agent = User.objects.create_user(email="other@test.com", password="x")
        other_permission = ProjectPermission.objects.create(
            project=self.project,
            user=other_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        second_queue = self.sector.queues.create(name="Queue 2")
        other_auth = QueueAuthorization.objects.create(
            permission=other_permission,
            queue=second_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self._list(mock_redis, f"?permission={self.permission.pk}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        returned_uuids = {item["uuid"] for item in results}
        self.assertIn(str(self.queue_auth.pk), returned_uuids)
        self.assertNotIn(str(other_auth.pk), returned_uuids)
