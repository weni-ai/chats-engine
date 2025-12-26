from datetime import date
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorHoliday


class OfficialHolidaysGETTests(APITestCase):
    """Tests for GET /api/v1/sector_holiday/official_holidays/"""

    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

    def test_get_official_holidays_without_project_param_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Parameter 'project' is required")

    def test_get_official_holidays_with_invalid_project_uuid_returns_404(self):
        response = self.client.get(
            self.url, {"project": "00000000-0000-0000-0000-000000000000"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Project not found")

    def test_get_official_holidays_without_permission_returns_403(self):
        other_user = User.objects.get(pk=1)
        other_token = Token.objects.get_or_create(user=other_user)[0]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + other_token.key)

        new_project = Project.objects.create(
            name="Project Without Permission", timezone="America/Sao_Paulo"
        )

        response = self.client.get(self.url, {"project": str(new_project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"], "You dont have permission in this project."
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_get_official_holidays_with_valid_project_and_year(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {
            date(2025, 1, 1): "New Year's Day",
            date(2025, 12, 25): "Christmas Day",
        }

        response = self.client.get(
            self.url, {"project": str(self.project.uuid), "year": "2025"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["country_code"], "BR")
        self.assertEqual(response.data["year"], 2025)
        self.assertEqual(len(response.data["holidays"]), 2)
        self.assertEqual(response.data["holidays"][0]["date"], "2025-01-01")
        self.assertEqual(response.data["holidays"][0]["name"], "New Year's Day")

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_get_official_holidays_without_year_uses_current_year(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        response = self.client.get(self.url, {"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("year", response.data)

    def test_get_official_holidays_with_invalid_year_returns_400(self):
        response = self.client.get(
            self.url, {"project": str(self.project.uuid), "year": "invalid"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Invalid 'year'. Use an integer like 2025."
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_get_official_holidays_returns_sorted_list(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {
            date(2025, 12, 25): "Christmas Day",
            date(2025, 1, 1): "New Year's Day",
            date(2025, 4, 21): "Tiradentes Day",
        }

        response = self.client.get(
            self.url, {"project": str(self.project.uuid), "year": "2025"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        holidays = response.data["holidays"]
        self.assertEqual(holidays[0]["date"], "2025-01-01")
        self.assertEqual(holidays[1]["date"], "2025-04-21")
        self.assertEqual(holidays[2]["date"], "2025-12-25")


class OfficialHolidaysPATCHTests(APITestCase):
    """Tests for PATCH /api/v1/sector_holiday/official_holidays/"""

    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.url = reverse("sector_holiday-official-holidays")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)

    def test_patch_without_sector_param_returns_400(self):
        response = self.client.patch(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Parameter 'sector' is required")

    def test_patch_with_invalid_sector_uuid_returns_404(self):
        response = self.client.patch(
            self.url + "?sector=00000000-0000-0000-0000-000000000000", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Sector not found")

    def test_patch_with_invalid_enabled_holidays_type_returns_400(self):
        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": "not_a_list"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "enabled_holidays and disabled_holidays must be lists",
        )

    def test_patch_with_invalid_disabled_holidays_type_returns_400(self):
        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": [], "disabled_holidays": "not_a_list"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "enabled_holidays and disabled_holidays must be lists",
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_enable_new_holiday_creates_record(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {date(2025, 1, 1): "New Year's Day"}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)
        self.assertEqual(response.data["disabled"], 0)
        self.assertEqual(response.data["errors"], [])

        holiday = SectorHoliday.objects.get(sector=self.sector, date=date(2025, 1, 1))
        self.assertEqual(holiday.day_type, SectorHoliday.CLOSED)
        self.assertEqual(holiday.description, "New Year's Day")
        self.assertFalse(holiday.its_custom)
        self.assertFalse(holiday.is_deleted)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_enable_existing_active_holiday_updates_record(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {date(2025, 1, 1): "New Year's Day"}

        existing_holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            description="Old Description",
            its_custom=True,
            is_deleted=False,
        )

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)

        existing_holiday.refresh_from_db()
        self.assertFalse(existing_holiday.is_deleted)
        self.assertFalse(existing_holiday.its_custom)
        self.assertEqual(existing_holiday.description, "New Year's Day")

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_disable_existing_holiday_marks_as_deleted(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        existing_holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            is_deleted=False,
        )

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"disabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["disabled"], 1)

        existing_holiday.refresh_from_db()
        self.assertTrue(existing_holiday.is_deleted)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_disable_already_deleted_holiday_does_not_count(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            is_deleted=True,
        )

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"disabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["disabled"], 0)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_disable_non_existing_holiday_does_nothing(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"disabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["disabled"], 0)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_with_invalid_date_format_returns_error_in_list(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["invalid-date", "01-01-2025", "2025/01/01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 0)
        self.assertEqual(len(response.data["errors"]), 3)
        self.assertIn("Invalid date format: invalid-date", response.data["errors"])
        self.assertIn("Invalid date format: 01-01-2025", response.data["errors"])
        self.assertIn("Invalid date format: 2025/01/01", response.data["errors"])

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_with_empty_string_date_returns_error(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["", "   "]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["errors"]), 2)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_with_non_string_date_returns_error(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": [123, None]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["errors"]), 2)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_enable_and_disable_multiple_holidays(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {
            date(2025, 1, 1): "New Year's Day",
            date(2025, 12, 25): "Christmas Day",
        }

        existing_holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 4, 21),
            day_type=SectorHoliday.CLOSED,
            is_deleted=False,
        )

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {
                "enabled_holidays": ["2025-01-01", "2025-12-25"],
                "disabled_holidays": ["2025-04-21"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 2)
        self.assertEqual(response.data["disabled"], 1)
        self.assertEqual(response.data["errors"], [])

        self.assertTrue(
            SectorHoliday.objects.filter(
                sector=self.sector, date=date(2025, 1, 1), is_deleted=False
            ).exists()
        )
        self.assertTrue(
            SectorHoliday.objects.filter(
                sector=self.sector, date=date(2025, 12, 25), is_deleted=False
            ).exists()
        )

        existing_holiday.refresh_from_db()
        self.assertTrue(existing_holiday.is_deleted)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_updates_existing_closed_holiday_keeps_day_type(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {date(2025, 1, 1): "New Year's Day"}

        existing_holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            is_deleted=False,
        )

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)

        existing_holiday.refresh_from_db()
        self.assertEqual(existing_holiday.day_type, SectorHoliday.CLOSED)
        self.assertEqual(existing_holiday.description, "New Year's Day")

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_with_dates_from_multiple_years(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.side_effect = lambda code, year: {
            date(year, 1, 1): f"New Year {year}"
        }

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2024-01-01", "2025-01-01", "2026-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 3)

        self.assertEqual(
            SectorHoliday.objects.get(
                sector=self.sector, date=date(2024, 1, 1)
            ).description,
            "New Year 2024",
        )
        self.assertEqual(
            SectorHoliday.objects.get(
                sector=self.sector, date=date(2025, 1, 1)
            ).description,
            "New Year 2025",
        )
        self.assertEqual(
            SectorHoliday.objects.get(
                sector=self.sector, date=date(2026, 1, 1)
            ).description,
            "New Year 2026",
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_with_date_not_in_official_holidays_creates_without_name(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-06-15"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)

        holiday = SectorHoliday.objects.get(sector=self.sector, date=date(2025, 6, 15))
        self.assertEqual(holiday.description, "")

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_does_not_update_if_no_changes_needed(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {date(2025, 1, 1): "New Year's Day"}

        existing_holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
            description="New Year's Day",
            its_custom=False,
            is_deleted=False,
        )
        original_modified = existing_holiday.modified_on

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["2025-01-01"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)

        existing_holiday.refresh_from_db()
        self.assertEqual(existing_holiday.modified_on, original_modified)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    def test_patch_with_whitespace_in_date_is_trimmed(
        self, mock_get_holidays, mock_get_country
    ):
        mock_get_country.return_value = "BR"
        mock_get_holidays.return_value = {date(2025, 1, 1): "New Year's Day"}

        response = self.client.patch(
            self.url + f"?sector={self.sector.uuid}",
            {"enabled_holidays": ["  2025-01-01  "]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)

        self.assertTrue(
            SectorHoliday.objects.filter(
                sector=self.sector, date=date(2025, 1, 1)
            ).exists()
        )
