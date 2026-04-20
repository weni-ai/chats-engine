from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.agents.views import (
    AgentQueuePermissionsView,
    UpdateQueuePermissionsView,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization


def _make_manager(project):
    """Creates a manager user with SectorAuthorization so is_manager() returns True."""
    user = User.objects.create_user(email="manager@test.com", password="x")
    perm = ProjectPermission.objects.create(
        project=project, user=user, role=ProjectPermission.ROLE_ADMIN
    )
    return user, perm


# ===========================================================================
# ENGAGE-7558 — GET /v1/agent/queue_permissions/?agent={email}&project={uuid}
# Returns all sectors/queues for an agent with agent_in_queue flag + chats_limit
# ===========================================================================


class AgentQueuePermissionsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager_user, _ = _make_manager(self.project)

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

    def _get(self, agent_email=None, project_uuid=None, user=None):
        view = AgentQueuePermissionsView.as_view()
        params = {}
        if agent_email is not None:
            params["agent"] = agent_email
        if project_uuid is not None:
            params["project"] = str(project_uuid)
        request = self.factory.get("/agent/queue_permissions/", params)
        force_authenticate(request, user=user or self.manager_user)
        return view(request)

    # ------------------------------------------------------------------
    # Case 1
    # ------------------------------------------------------------------

    def test_returns_queue_permissions_with_agent_in_queue_flag(self):
        """Returns sector/queue structure with agent_in_queue=True for authorised queues."""
        response = self._get(
            agent_email=self.agent_user.email,
            project_uuid=self.project.pk,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("queue_permissions", response.data)
        self.assertIn("chats_limit", response.data)

        sector_entry = response.data["queue_permissions"][0]
        self.assertEqual(sector_entry["sector"]["name"], self.sector.name)

        queues = sector_entry["sector"]["queues"]
        queue_entry = next(q for q in queues if q["uuid"] == str(self.queue.pk))
        self.assertTrue(queue_entry["agent_in_queue"])

    # ------------------------------------------------------------------
    # Case 2
    # ------------------------------------------------------------------

    def test_agent_not_in_queue_returns_agent_in_queue_false(self):
        """Queues the agent does NOT belong to have agent_in_queue=False."""
        second_queue = self.sector.queues.create(name="Queue 2")

        response = self._get(
            agent_email=self.agent_user.email,
            project_uuid=self.project.pk,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queues = response.data["queue_permissions"][0]["sector"]["queues"]
        second = next(q for q in queues if q["uuid"] == str(second_queue.pk))
        self.assertFalse(second["agent_in_queue"])

    # ------------------------------------------------------------------
    # Case 3
    # ------------------------------------------------------------------

    def test_unauthenticated_returns_401(self):
        """Returns 401 when no authentication credentials are provided."""
        view = AgentQueuePermissionsView.as_view()
        request = self.factory.get(
            "/agent/queue_permissions/",
            {"agent": self.agent_user.email, "project": str(self.project.pk)},
        )
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Case 4
    # ------------------------------------------------------------------

    def test_non_manager_returns_403(self):
        """Returns 403 when the requesting user is not a manager."""
        regular_user = User.objects.create_user(email="regular@test.com", password="x")
        ProjectPermission.objects.create(
            project=self.project,
            user=regular_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        response = self._get(
            agent_email=self.agent_user.email,
            project_uuid=self.project.pk,
            user=regular_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # Case 5
    # ------------------------------------------------------------------

    def test_returns_all_sectors_even_without_agent_authorization(self):
        """All project sectors are returned regardless of the agent's membership."""
        second_sector = self.project.sectors.create(
            name="Billing", rooms_limit=3, work_start="09:00", work_end="17:00"
        )
        second_sector.queues.create(name="Billing Queue")

        response = self._get(
            agent_email=self.agent_user.email,
            project_uuid=self.project.pk,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sector_names = [e["sector"]["name"] for e in response.data["queue_permissions"]]
        self.assertIn(self.sector.name, sector_names)
        self.assertIn(second_sector.name, sector_names)

    # ------------------------------------------------------------------
    # Case 6
    # ------------------------------------------------------------------

    def test_nonexistent_agent_returns_404(self):
        """Returns 404 when the agent email does not belong to the project."""
        response = self._get(
            agent_email="ghost@test.com",
            project_uuid=self.project.pk,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ===========================================================================
# ENGAGE-7557 — POST /v1/agent/update_queue_permissions/
# Single endpoint handling add, remove and bulk operations
# ===========================================================================


class UpdateQueuePermissionsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager_user, _ = _make_manager(self.project)

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

    def _post(self, data, user=None):
        view = UpdateQueuePermissionsView.as_view()
        request = self.factory.post(
            "/agent/update_queue_permissions/", data, format="json"
        )
        force_authenticate(request, user=user or self.manager_user)
        return view(request)

    def _base_body(self, **overrides):
        body = {
            "agents": [self.agent_user.email],
            "project": str(self.project.pk),
        }
        body.update(overrides)
        return body

    # ------------------------------------------------------------------
    # Case 7
    # ------------------------------------------------------------------

    def test_add_agent_to_queue_creates_authorization(self):
        """to_add creates a new QueueAuthorization for the agent."""
        second_queue = self.sector.queues.create(name="Queue 2")

        response = self._post(self._base_body(to_add=[str(second_queue.pk)]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=second_queue
            ).exists()
        )

    # ------------------------------------------------------------------
    # Case 8
    # ------------------------------------------------------------------

    def test_add_agent_to_queue_is_idempotent(self):
        """Adding the agent to a queue they already belong to does not raise an error."""
        response = self._post(self._base_body(to_add=[str(self.queue.pk)]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=self.queue
            ).count(),
            1,
        )

    # ------------------------------------------------------------------
    # Case 9
    # ------------------------------------------------------------------

    def test_remove_agent_from_queue_deletes_authorization(self):
        """to_remove deletes the QueueAuthorization for the agent."""
        response = self._post(self._base_body(to_remove=[str(self.queue.pk)]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=self.queue
            ).exists()
        )

    # ------------------------------------------------------------------
    # Case 10
    # ------------------------------------------------------------------

    def test_update_chats_limit_saves_on_permission(self):
        """chats_limit updates is_custom_limit_active and custom_rooms_limit on ProjectPermission."""
        response = self._post(self._base_body(chats_limit={"active": True, "total": 8}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.permission.refresh_from_db()
        self.assertTrue(self.permission.is_custom_limit_active)
        self.assertEqual(self.permission.custom_rooms_limit, 8)

    # ------------------------------------------------------------------
    # Case 11
    # ------------------------------------------------------------------

    def test_bulk_operation_applies_to_all_agents_in_list(self):
        """When agents has multiple entries, changes apply to all of them."""
        second_agent = User.objects.create_user(email="agent2@test.com", password="x")
        second_perm = ProjectPermission.objects.create(
            project=self.project,
            user=second_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        second_queue = self.sector.queues.create(name="Queue 2")

        response = self._post(
            {
                "agents": [self.agent_user.email, second_agent.email],
                "project": str(self.project.pk),
                "to_add": [str(second_queue.pk)],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=second_queue
            ).exists()
        )
        self.assertTrue(
            QueueAuthorization.objects.filter(
                permission=second_perm, queue=second_queue
            ).exists()
        )

    # ------------------------------------------------------------------
    # Case 12
    # ------------------------------------------------------------------

    def test_agent_not_in_project_returns_400(self):
        """Returns 400 when an agent email does not exist in the project."""
        response = self._post(
            self._base_body(
                agents=["ghost@test.com"],
                to_add=[str(self.queue.pk)],
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Case 13
    # ------------------------------------------------------------------

    def test_missing_required_fields_returns_400(self):
        """Returns 400 when none of to_add, to_remove, or chats_limit is provided."""
        response = self._post(
            {
                "agents": [self.agent_user.email],
                "project": str(self.project.pk),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Case 14
    # ------------------------------------------------------------------

    def test_add_and_remove_in_same_request(self):
        """to_add and to_remove can be combined in a single request."""
        second_queue = self.sector.queues.create(name="Queue 2")

        response = self._post(
            self._base_body(
                to_add=[str(second_queue.pk)],
                to_remove=[str(self.queue.pk)],
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=second_queue
            ).exists()
        )
        self.assertFalse(
            QueueAuthorization.objects.filter(
                permission=self.permission, queue=self.queue
            ).exists()
        )
