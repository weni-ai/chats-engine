import uuid

from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.projects.usecases.project_update import (
    ProjectUpdateDTO,
    ProjectUpdateUseCase,
)


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
