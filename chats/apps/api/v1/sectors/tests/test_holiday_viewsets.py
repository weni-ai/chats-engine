from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.sectors.viewsets import SectorHolidayViewSet
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector, SectorHoliday


class OfficialHolidaysGetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="agent@test.com")
        self.project = Project.objects.create(name="Test Project", timezone="America/Sao_Paulo")
        self.sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=5,
        )
        ProjectPermission.objects.create(project=self.project, user=self.user, role=1)
        self.view = SectorHolidayViewSet.as_view({"get": "official_holidays"})

    def test_get_requires_project_param(self):
        request = self.factory.get("/official_holidays/")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project", response.data["detail"].lower())

    def test_get_returns_404_for_nonexistent_project(self):
        request = self.factory.get("/official_holidays/?project=00000000-0000-0000-0000-000000000000")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_returns_403_for_user_without_permission(self):
        other_user = User.objects.create(email="other@test.com")
        request = self.factory.get(f"/official_holidays/?project={self.project.uuid}")
        force_authenticate(request, user=other_user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_get_returns_holidays_for_project(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {
            date(2025, 1, 1): "New Year",
            date(2025, 12, 25): "Christmas",
        }
        request = self.factory.get(f"/official_holidays/?project={self.project.uuid}&year=2025")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["country_code"], "BR")
        self.assertEqual(response.data["year"], 2025)
        self.assertEqual(len(response.data["holidays"]), 2)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_get_uses_current_year_when_not_provided(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {}
        request = self.factory.get(f"/official_holidays/?project={self.project.uuid}")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("year", response.data)

    def test_get_returns_400_for_invalid_year(self):
        request = self.factory.get(f"/official_holidays/?project={self.project.uuid}&year=invalid")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OfficialHolidaysPatchTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="agent@test.com")
        self.project = Project.objects.create(name="Test Project", timezone="America/Sao_Paulo")
        self.sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=5,
        )
        ProjectPermission.objects.create(project=self.project, user=self.user, role=1)
        self.view = SectorHolidayViewSet.as_view({"patch": "official_holidays"})

    def test_patch_requires_sector_param(self):
        request = self.factory.patch(
            "/official_holidays/",
            data={"enabled_holidays": [], "disabled_holidays": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector", response.data["detail"].lower())

    def test_patch_returns_404_for_nonexistent_sector(self):
        request = self.factory.patch(
            "/official_holidays/?sector=00000000-0000-0000-0000-000000000000",
            data={"enabled_holidays": [], "disabled_holidays": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_requires_list_types(self):
        request = self.factory.patch(
            f"/official_holidays/?sector={self.sector.uuid}",
            data={"enabled_holidays": "invalid", "disabled_holidays": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_enables_holidays(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {date(2025, 12, 25): "Christmas"}
        
        request = self.factory.patch(
            f"/official_holidays/?sector={self.sector.uuid}",
            data={"enabled_holidays": ["2025-12-25"], "disabled_holidays": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)
        self.assertEqual(response.data["disabled"], 0)
        self.assertTrue(
            SectorHoliday.objects.filter(
                sector=self.sector, date=date(2025, 12, 25), is_deleted=False
            ).exists()
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_disables_existing_holiday(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {date(2025, 12, 25): "Christmas"}
        
        holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 12, 25),
            day_type=SectorHoliday.CLOSED,
        )
        
        request = self.factory.patch(
            f"/official_holidays/?sector={self.sector.uuid}",
            data={"enabled_holidays": [], "disabled_holidays": ["2025-12-25"]},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["disabled"], 1)
        holiday.refresh_from_db()
        self.assertTrue(holiday.is_deleted)

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_reports_invalid_date_format(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {}
        
        request = self.factory.patch(
            f"/official_holidays/?sector={self.sector.uuid}",
            data={"enabled_holidays": ["invalid-date"], "disabled_holidays": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 0)
        self.assertIn("invalid-date", response.data["errors"][0])

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_handles_both_enable_and_disable(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {
            date(2025, 12, 25): "Christmas",
            date(2025, 1, 1): "New Year",
        }
        
        existing = SectorHoliday.objects.create(
            sector=self.sector,
            date=date(2025, 1, 1),
            day_type=SectorHoliday.CLOSED,
        )
        
        request = self.factory.patch(
            f"/official_holidays/?sector={self.sector.uuid}",
            data={
                "enabled_holidays": ["2025-12-25"],
                "disabled_holidays": ["2025-01-01"],
            },
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)
        self.assertEqual(response.data["disabled"], 1)
        
        existing.refresh_from_db()
        self.assertTrue(existing.is_deleted)
        self.assertTrue(
            SectorHoliday.objects.filter(
                sector=self.sector, date=date(2025, 12, 25), is_deleted=False
            ).exists()
        )

    @patch("chats.apps.api.v1.sectors.viewsets.get_country_holidays")
    @patch("chats.apps.api.v1.sectors.viewsets.get_country_from_timezone")
    def test_patch_creates_new_holiday_when_not_exists(self, mock_country, mock_holidays):
        mock_country.return_value = "BR"
        mock_holidays.return_value = {date(2025, 7, 9): "Revolução Constitucionalista"}
        
        self.assertFalse(
            SectorHoliday.objects.filter(sector=self.sector, date=date(2025, 7, 9)).exists()
        )
        
        request = self.factory.patch(
            f"/official_holidays/?sector={self.sector.uuid}",
            data={"enabled_holidays": ["2025-07-09"], "disabled_holidays": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["enabled"], 1)
        
        holiday = SectorHoliday.objects.get(sector=self.sector, date=date(2025, 7, 9))
        self.assertFalse(holiday.is_deleted)
        self.assertEqual(holiday.day_type, SectorHoliday.CLOSED)
