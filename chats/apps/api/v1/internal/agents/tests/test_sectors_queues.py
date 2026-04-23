from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.agents.views import SectorsQueuesView
from chats.apps.projects.models import Project, ProjectPermission


def _make_manager(project):
    user = User.objects.create_user(email="manager@test.com", password="x")
    ProjectPermission.objects.create(
        project=project, user=user, role=ProjectPermission.ROLE_ADMIN
    )
    return user


# ===========================================================================
# GET /v1/project/{project_uuid}/sectors/queues/?sectors=uuid1,uuid2
# Returns queues grouped by sector for the requested sector UUIDs
# ===========================================================================


class SectorsQueuesViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

        self.sector_a = self.project.sectors.create(
            name="Sector A", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.sector_b = self.project.sectors.create(
            name="Sector B", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue_a1 = self.sector_a.queues.create(name="Queue A1")
        self.queue_a2 = self.sector_a.queues.create(name="Queue A2")
        self.queue_b1 = self.sector_b.queues.create(name="Queue B1")

    def _get(self, sectors=None, user=None, project_uuid=None):
        view = SectorsQueuesView.as_view()
        params = {}
        if sectors is not None:
            params["sectors"] = sectors

        url = f"/project/{project_uuid or self.project.pk}/sectors/queues/"
        request = self.factory.get(url, params)
        force_authenticate(request, user=user or self.manager)
        return view(request, project_uuid=str(project_uuid or self.project.pk))

    def test_returns_queues_for_single_sector(self):
        """Passing one sector UUID returns that sector with its queues."""
        response = self._get(sectors=str(self.sector_a.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Sector A")
        self.assertEqual(results[0]["uuid"], str(self.sector_a.uuid))

        queue_names = [q["name"] for q in results[0]["queues"]]
        self.assertEqual(sorted(queue_names), ["Queue A1", "Queue A2"])

    def test_returns_queues_for_multiple_sectors(self):
        """Passing comma-separated UUIDs returns all requested sectors."""
        response = self._get(
            sectors=f"{self.sector_a.pk},{self.sector_b.pk}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        sector_names = {r["name"] for r in results}
        self.assertEqual(sector_names, {"Sector A", "Sector B"})

    def test_queues_include_uuid_and_name(self):
        """Each queue in the response contains uuid and name."""
        response = self._get(sectors=str(self.sector_a.pk))

        queue = response.data["results"][0]["queues"][0]
        self.assertIn("uuid", queue)
        self.assertIn("name", queue)

    def test_without_sectors_param_returns_empty_list(self):
        """When no `sectors` query param is provided, results is an empty list."""
        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"results": []})

    def test_empty_sectors_param_returns_empty_list(self):
        """An empty `sectors` query param returns an empty list."""
        response = self._get(sectors="")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"results": []})

    def test_deleted_sector_is_ignored(self):
        """Deleted sectors are not returned, even when explicitly requested."""
        self.sector_a.is_deleted = True
        self.sector_a.save(update_fields=["is_deleted"])

        response = self._get(
            sectors=f"{self.sector_a.pk},{self.sector_b.pk}"
        )

        sector_names = {r["name"] for r in response.data["results"]}
        self.assertNotIn("Sector A", sector_names)
        self.assertIn("Sector B", sector_names)

    def test_deleted_queues_are_filtered_out(self):
        """Deleted queues do not appear in the response."""
        self.queue_a1.is_deleted = True
        self.queue_a1.save(update_fields=["is_deleted"])

        response = self._get(sectors=str(self.sector_a.pk))

        results = response.data["results"]
        queue_names = [q["name"] for q in results[0]["queues"]]
        self.assertNotIn("Queue A1", queue_names)
        self.assertIn("Queue A2", queue_names)

    def test_sectors_from_other_projects_are_not_returned(self):
        """Sectors from other projects cannot be queried even with valid UUIDs."""
        other_project = Project.objects.create(name="Other", timezone="UTC")
        other_sector = other_project.sectors.create(
            name="Foreign",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

        response = self._get(
            sectors=f"{self.sector_a.pk},{other_sector.pk}"
        )

        sector_names = {r["name"] for r in response.data["results"]}
        self.assertIn("Sector A", sector_names)
        self.assertNotIn("Foreign", sector_names)

    def test_unauthenticated_returns_401(self):
        """Returns 401 when the request is unauthenticated."""
        view = SectorsQueuesView.as_view()
        request = self.factory.get(
            f"/project/{self.project.pk}/sectors/queues/",
            {"sectors": str(self.sector_a.pk)},
        )
        response = view(request, project_uuid=str(self.project.pk))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_manager_returns_403(self):
        """Non-manager users receive 403."""
        regular_user = User.objects.create_user(email="regular@test.com", password="x")
        ProjectPermission.objects.create(
            project=self.project,
            user=regular_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        response = self._get(
            sectors=str(self.sector_a.pk),
            user=regular_user,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sector_with_no_active_queues_returns_empty_queues_list(self):
        """A sector with all queues deleted returns with an empty queues list."""
        self.queue_a1.is_deleted = True
        self.queue_a1.save(update_fields=["is_deleted"])
        self.queue_a2.is_deleted = True
        self.queue_a2.save(update_fields=["is_deleted"])

        response = self._get(sectors=str(self.sector_a.pk))

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["queues"], [])
