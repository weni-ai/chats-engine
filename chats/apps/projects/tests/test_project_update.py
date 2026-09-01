import uuid
from datetime import date, time
from unittest.mock import patch

from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.projects.usecases.project_update import (
    ProjectUpdateDTO,
    ProjectUpdateUseCase,
)
from chats.apps.sectors.models import Sector, SectorHoliday


class TestProjectUpdateUseCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Original Name",
            timezone="UTC",
            date_format="D",
            config={"existing_key": "existing_value"},
        )
        self.use_case = ProjectUpdateUseCase()

    def test_update_name(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            name="Updated Name",
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(project.name, "Updated Name")

    def test_update_timezone(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            timezone="America/Sao_Paulo",
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(str(project.timezone), "America/Sao_Paulo")

    def test_update_date_format(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            date_format="M",
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(project.date_format, "M")

    def test_update_config_merges_with_existing(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            config={"new_key": "new_value"},
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(
            project.config,
            {"existing_key": "existing_value", "new_key": "new_value"},
        )

    def test_update_config_overwrites_existing_keys(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            config={"existing_key": "overwritten_value"},
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(project.config, {"existing_key": "overwritten_value"})

    def test_update_multiple_fields(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            name="New Name",
            timezone="America/Fortaleza",
            date_format="M",
            config={"extra": True},
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(project.name, "New Name")
        self.assertEqual(str(project.timezone), "America/Fortaleza")
        self.assertEqual(project.date_format, "M")
        self.assertEqual(
            project.config,
            {"existing_key": "existing_value", "extra": True},
        )

    def test_update_with_no_fields_does_not_save(self):
        original_modified = self.project.modified_on

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
        )

        self.use_case.update_project(dto)

        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Original Name")
        self.assertEqual(self.project.modified_on, original_modified)

    def test_update_nonexistent_project_raises(self):
        dto = ProjectUpdateDTO(
            project_uuid=str(uuid.uuid4()),
            user_email="user@test.com",
            name="Does Not Matter",
        )

        with self.assertRaises(Project.DoesNotExist):
            self.use_case.update_project(dto)

    def test_update_config_on_project_with_null_config(self):
        self.project.config = None
        self.project.save()

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            config={"brand_new": "config"},
        )

        project = self.use_case.update_project(dto)

        project.refresh_from_db()
        self.assertEqual(project.config, {"brand_new": "config"})

    def _create_holiday(self, project, holiday_date=None):
        sector = Sector.objects.create(
            name="Support",
            project=project,
            rooms_limit=5,
            work_start=time(8, 0),
            work_end=time(18, 0),
        )
        return SectorHoliday.objects.create(
            sector=sector,
            date=holiday_date or date(2026, 8, 17),
            day_type=SectorHoliday.CLOSED,
            description="Official holiday",
        )

    def test_update_timezone_deletes_sector_holidays(self):
        holiday = self._create_holiday(self.project)

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            timezone="America/Sao_Paulo",
        )

        self.use_case.update_project(dto)

        holiday.refresh_from_db()
        self.assertTrue(holiday.is_deleted)

    def test_same_timezone_does_not_delete_sector_holidays(self):
        holiday = self._create_holiday(self.project)

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            timezone="UTC",
        )

        self.use_case.update_project(dto)

        holiday.refresh_from_db()
        self.assertFalse(holiday.is_deleted)

    def test_update_name_does_not_delete_sector_holidays(self):
        holiday = self._create_holiday(self.project)

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            name="Updated Name",
        )

        self.use_case.update_project(dto)

        holiday.refresh_from_db()
        self.assertFalse(holiday.is_deleted)

    def test_timezone_change_does_not_delete_holidays_from_other_projects(self):
        other_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Other Project",
            timezone="UTC",
        )
        other_holiday = self._create_holiday(other_project)
        self._create_holiday(self.project)

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            timezone="America/Sao_Paulo",
        )

        self.use_case.update_project(dto)

        other_holiday.refresh_from_db()
        self.assertFalse(other_holiday.is_deleted)

    @patch("chats.apps.sectors.utils.CacheClient")
    def test_timezone_change_invalidates_holiday_cache(self, mock_cache_client_cls):
        mock_cache_client = mock_cache_client_cls.return_value
        holiday = self._create_holiday(self.project, holiday_date=date(2026, 8, 17))

        dto = ProjectUpdateDTO(
            project_uuid=str(self.project.uuid),
            user_email="user@test.com",
            timezone="America/Sao_Paulo",
        )
        self.use_case.update_project(dto)

        mock_cache_client.delete.assert_any_call(
            f"holiday:{holiday.sector.uuid}:2026-08-17"
        )
