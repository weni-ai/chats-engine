from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.agents.views import UpdateQueuePermissionsView
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization
from chats.apps.rooms.models import Room


def _make_manager(project):
    user = User.objects.create_user(email="manager@test.com", password="x")
    perm = ProjectPermission.objects.create(
        project=project, user=user, role=ProjectPermission.ROLE_ADMIN
    )
    return user, perm


# ===========================================================================
# ENGAGE-7554 — Individual attendance limit per agent (on ProjectPermission)
#
# Default behaviour: agent inherits sector.rooms_limit.
# When is_custom_limit_active=True + custom_rooms_limit set: overrides the
# sector value for that specific agent — no impact on other 99 agents.
# ===========================================================================


class CustomRoomsLimitModelTests(TestCase):
    """Queue.available_agents respects per-agent custom limits stored on ProjectPermission."""

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
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
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
        # Agent has reached the sector limit (2 active rooms, limit = 2)
        self._fill_active_rooms(2)

        self.assertNotIn(self.agent_user, self.queue.available_agents)

    # ------------------------------------------------------------------
    # Case 16
    # ------------------------------------------------------------------

    def test_custom_limit_allows_agent_when_sector_limit_exceeded(self):
        """When is_custom_limit_active=True, custom_rooms_limit replaces the sector limit."""
        self.permission.is_custom_limit_active = True
        self.permission.custom_rooms_limit = 5
        self.permission.save(
            update_fields=["is_custom_limit_active", "custom_rooms_limit"]
        )

        # 2 active rooms exceed sector.rooms_limit (2) but not custom_rooms_limit (5)
        self._fill_active_rooms(2)

        self.assertIn(self.agent_user, self.queue.available_agents)


class CustomRoomsLimitAPITests(TestCase):
    """API tests for the chats_limit field via update_queue_permissions."""

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

    def _post(self, data):
        view = UpdateQueuePermissionsView.as_view()
        request = self.factory.post(
            "/agent/update_queue_permissions/", data, format="json"
        )
        force_authenticate(request, user=self.manager_user)
        return view(request)

    # ------------------------------------------------------------------
    # Case 17
    # ------------------------------------------------------------------

    def test_update_sets_custom_limit_on_permission(self):
        """Posting chats_limit persists is_custom_limit_active and custom_rooms_limit."""
        response = self._post(
            {
                "agents": [self.agent_user.email],
                "project": str(self.project.pk),
                "chats_limit": {"active": True, "total": 10},
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.permission.refresh_from_db()
        self.assertTrue(self.permission.is_custom_limit_active)
        self.assertEqual(self.permission.custom_rooms_limit, 10)

    # ------------------------------------------------------------------
    # Case 18
    # ------------------------------------------------------------------

    def test_update_deactivates_custom_limit(self):
        """Setting active=False disables the custom limit without removing the stored value."""
        self.permission.is_custom_limit_active = True
        self.permission.custom_rooms_limit = 10
        self.permission.save(
            update_fields=["is_custom_limit_active", "custom_rooms_limit"]
        )

        response = self._post(
            {
                "agents": [self.agent_user.email],
                "project": str(self.project.pk),
                "chats_limit": {"active": False, "total": None},
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.permission.refresh_from_db()
        self.assertFalse(self.permission.is_custom_limit_active)

    # ------------------------------------------------------------------
    # Case 19
    # ------------------------------------------------------------------

    def test_custom_limit_fields_default_to_inactive(self):
        """is_custom_limit_active defaults to False and custom_rooms_limit defaults to None."""
        fresh_user = User.objects.create_user(email="fresh@test.com", password="x")
        perm = ProjectPermission.objects.create(
            project=self.project,
            user=fresh_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.assertFalse(perm.is_custom_limit_active)
        self.assertIsNone(perm.custom_rooms_limit)
