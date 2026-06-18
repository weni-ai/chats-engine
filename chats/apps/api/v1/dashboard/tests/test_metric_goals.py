from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.dashboard.models import MetricGoal
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector, SectorAuthorization


class MetricGoalsViewsetTestCase(APITestCase):
    def setUp(self):
        self.manager, self.manager_token = create_user_and_token("metricmanager")
        self.viewer, self.viewer_token = create_user_and_token("metricviewer")
        self.attendant, self.attendant_token = create_user_and_token("metricattendant")

        self.project = Project.objects.create(name="Metric Goals Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
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

        self.viewer_permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.viewer,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=self.viewer_permission,
            sector=self.sector,
            role=SectorAuthorization.ROLE_NOT_SETTED,
        )

        ProjectPermission.objects.create(
            project=self.project,
            user=self.attendant,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.list_url = reverse(
            "project-metric-goals-list",
            kwargs={"uuid": str(self.project.uuid)},
        )
        self.upsert_url = reverse(
            "project-metric-goals-detail",
            kwargs={
                "uuid": str(self.project.uuid),
                "metric": MetricGoal.METRIC_WAITING_TIME,
            },
        )
        self.delete_url = reverse(
            "project-metric-goals-detail",
            kwargs={
                "uuid": str(self.project.uuid),
                "metric": MetricGoal.METRIC_WAITING_TIME,
            },
        )

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_list_returns_only_configured_goals(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_MINUTE,
        )
        self._auth(self.manager_token)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["goals"]), 1)
        self.assertEqual(
            response.data["goals"][0]["metric"],
            MetricGoal.METRIC_WAITING_TIME,
        )
        self.assertEqual(response.data["goals"][0]["threshold_seconds"], 300)
        self.assertEqual(response.data["goals"][0]["unit"], MetricGoal.UNIT_MINUTE)
        self.assertEqual(response.data["goals"][0]["threshold_value"], 5)

    def test_list_empty_when_no_goals_configured(self):
        self._auth(self.manager_token)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["goals"], [])

    def test_viewer_can_list_goals(self):
        self._auth(self.viewer_token)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_attendant_without_dashboard_access_cannot_list_goals(self):
        self._auth(self.attendant_token)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_goal_with_threshold_and_unit(self):
        self._auth(self.manager_token)

        response = self.client.post(
            self.upsert_url,
            {
                "threshold": 5,
                "unit": MetricGoal.UNIT_MINUTE,
                "is_active": True,
                "email_enabled": True,
                "rooms_threshold_count": 5,
                "recipients": [
                    {
                        "uuid_project_permission": str(
                            self.viewer_permission.uuid
                        )
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["threshold_seconds"], 300)
        self.assertEqual(response.data["threshold_value"], 5)
        self.assertEqual(response.data["unit"], MetricGoal.UNIT_MINUTE)
        self.assertEqual(response.data["rooms_threshold_count"], 5)
        self.assertTrue(response.data["email_enabled"])
        self.assertEqual(len(response.data["recipients"]), 1)
        self.assertEqual(
            response.data["recipients"][0]["email"],
            self.viewer.email,
        )

    def test_manager_can_update_existing_goal(self):
        goal = MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=120,
            unit=MetricGoal.UNIT_SECOND,
        )
        goal.recipients.add(self.viewer_permission)
        self._auth(self.manager_token)

        response = self.client.post(
            self.upsert_url,
            {
                "threshold_seconds": 600,
                "unit": MetricGoal.UNIT_SECOND,
                "is_active": False,
                "email_enabled": False,
                "rooms_threshold_count": 3,
                "recipients": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["threshold_seconds"], 600)
        self.assertFalse(response.data["is_active"])
        self.assertEqual(response.data["rooms_threshold_count"], 3)
        self.assertEqual(response.data["recipients"], [])

    def test_viewer_cannot_configure_goal(self):
        self._auth(self.viewer_token)

        response = self.client.post(
            self.upsert_url,
            {"threshold_seconds": 300, "unit": MetricGoal.UNIT_SECOND},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_metric_returns_400(self):
        self._auth(self.manager_token)
        url = reverse(
            "project-metric-goals-detail",
            kwargs={
                "uuid": str(self.project.uuid),
                "metric": "invalid_metric",
            },
        )

        response = self.client.post(
            url,
            {"threshold_seconds": 300, "unit": MetricGoal.UNIT_SECOND},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attendant_cannot_be_recipient(self):
        attendant_permission = ProjectPermission.objects.get(
            project=self.project,
            user=self.attendant,
        )
        self._auth(self.manager_token)

        response = self.client.post(
            self.upsert_url,
            {
                "threshold_seconds": 300,
                "unit": MetricGoal.UNIT_SECOND,
                "recipients": [
                    {
                        "uuid_project_permission": str(
                            attendant_permission.uuid
                        )
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_can_delete_goal(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
        )
        self._auth(self.manager_token)

        response = self.client.delete(self.delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            MetricGoal.objects.filter(
                project=self.project,
                metric=MetricGoal.METRIC_WAITING_TIME,
            ).exists()
        )

    def test_delete_unconfigured_metric_returns_404(self):
        self._auth(self.manager_token)

        response = self.client.delete(self.delete_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_viewer_cannot_delete_goal(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
        )
        self._auth(self.viewer_token)

        response = self.client.delete(self.delete_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
