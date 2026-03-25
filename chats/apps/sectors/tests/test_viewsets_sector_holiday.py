from datetime import date
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector, SectorHoliday


class SectorHolidayOfficialHolidaysTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.wrong_user = User.objects.get(pk=1)
        self.wrong_login_token = Token.objects.get_or_create(user=self.wrong_user)[0]

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_get_official_holidays_success(self, mock_tz, mock_holidays):
        mock_tz.return_value = "BR"
        mock_holidays.return_value = {
            date(2025, 1, 1): "Ano Novo",
            date(2025, 12, 25): "Natal",
        }

        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = self.client.get(
            url, {"project": str(self.project.uuid), "year": 2025}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["country_code"], "BR")
        self.assertEqual(response.data["year"], 2025)
        self.assertEqual(len(response.data["holidays"]), 2)

    def test_get_official_holidays_missing_project(self):
        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project", response.data["detail"].lower())

    def test_get_official_holidays_project_not_found(self):
        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = self.client.get(
            url, {"project": "00000000-0000-0000-0000-000000000000"}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_official_holidays_no_permission(self):
        ProjectPermission.objects.filter(
            user=self.wrong_user, project=self.project
        ).delete()

        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(
            HTTP_AUTHORIZATION="Token " + self.wrong_login_token.key
        )
        response = self.client.get(url, {"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_official_holidays_invalid_year(self):
        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = self.client.get(
            url, {"project": str(self.project.uuid), "year": "invalid"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_official_holidays_enable(self, mock_tz, mock_holidays):
        mock_tz.return_value = "BR"
        mock_holidays.return_value = {date(2025, 1, 1): "Ano Novo"}

        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)
        self.assertTrue(
            SectorHoliday.objects.filter(
                sector=self.sector, date=date(2025, 1, 1), is_deleted=False
            ).exists()
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_official_holidays_disable(self, mock_tz, mock_holidays):
        mock_tz.return_value = "BR"
        mock_holidays.return_value = {date(2025, 1, 1): "Ano Novo"}

        SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            description="Ano Novo",
            is_deleted=False,
        )

        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url + f"?sector={self.sector.uuid}",
            {"disabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["disabled"], 1)
        holiday = SectorHoliday.all_objects.get(
            sector=self.sector, date=date(2025, 1, 1)
        )
        self.assertTrue(holiday.is_deleted)

    def test_patch_official_holidays_missing_sector(self):
        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url, {"enabled_holidays": ["2025-01-01"]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector", response.data["detail"].lower())

    def test_patch_official_holidays_sector_not_found(self):
        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url + "?sector=00000000-0000-0000-0000-000000000000",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_official_holidays_invalid_lists(self):
        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": "not-a-list"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_official_holidays_invalid_date_format(self, mock_tz, mock_holidays):
        mock_tz.return_value = "BR"
        mock_holidays.return_value = {}

        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["invalid-date", "2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Invalid date format: invalid-date", response.data["errors"])

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_official_holidays_update_existing_not_deleted(
        self, mock_tz, mock_holidays
    ):
        mock_tz.return_value = "BR"
        mock_holidays.return_value = {date(2025, 1, 1): "Ano Novo"}

        existing = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            description="Old Name",
            its_custom=True,
            is_deleted=False,
        )

        url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

        response = self.client.patch(
            url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        existing.refresh_from_db()
        self.assertFalse(existing.is_deleted)
        self.assertEqual(existing.day_type, SectorHoliday.CLOSED)
        self.assertFalse(existing.its_custom)
        self.assertEqual(existing.description, "Ano Novo")
