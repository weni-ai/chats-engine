import uuid
from unittest.mock import MagicMock
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission, TemplateType
from chats.apps.projects.usecases.exceptions import InvalidProjectData
from chats.apps.projects.usecases.project_creation import (
    ProjectCreationDTO,
    ProjectCreationUseCase,
)


class TestProjectCreationUsecase(TestCase):
    def setUp(self):
        """Set up test data and dependencies."""
        self.sector_setup_handler = MagicMock()
        self.sector_setup_handler.setup_sectors_in_project = MagicMock()

        self.use_case = ProjectCreationUseCase(self.sector_setup_handler)

        self.user_email = "test@example.com"
        self.user, _ = User.objects.get_or_create(email=self.user_email)

        self.org_uuid = str(uuid.uuid4())

        self.template_type, _ = TemplateType.objects.get_or_create(
            name="Test Template Type", defaults={"setup": {"sectors": []}}
        )

        self.project_dto = self._create_base_project_dto()

    def _create_base_project_dto(self, **kwargs):
        """Create a base ProjectCreationDTO with default values that can be overridden."""
        default_values = {
            "uuid": str(uuid.uuid4()),
            "name": "Test Project",
            "is_template": False,
            "user_email": self.user_email,
            "date_format": "D",
            "timezone": str(timezone.get_current_timezone()),
            "template_type_uuid": str(self.template_type.uuid),
            "authorizations": [],
            "org": self.org_uuid,
        }
        default_values.update(kwargs)
        return ProjectCreationDTO(**default_values)

    def _create_principal_project(self, org_uuid=None):
        """Helper method to create a principal project in the specified org."""
        org = org_uuid or self.org_uuid
        return Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Principal Project",
            org=org,
            config={"its_principal": True},
        )

    def _create_test_users(self, count=2):
        """Helper method to create test users."""
        users = []
        for i in range(count):
            email = f"user{i+1}@example.com"
            user, _ = User.objects.get_or_create(email=email)
            users.append(user)
        return users

    @patch("chats.apps.projects.tasks.send_secondary_project_to_insights.delay")
    def test_create_project(self, mock_send_secondary_project_to_insights):
        """Test creating a regular project without any special configuration."""
        mock_send_secondary_project_to_insights.return_value = MagicMock()
        mock_send_secondary_project_to_insights.delay.assert_not_called()

        self.use_case.create_project(self.project_dto)

        project = Project.objects.get(uuid=self.project_dto.uuid)

        self.assertEqual(project.name, self.project_dto.name)
        self.assertEqual(str(project.uuid), self.project_dto.uuid)
        self.assertEqual(project.is_template, self.project_dto.is_template)
        self.assertEqual(project.date_format, self.project_dto.date_format)
        self.assertEqual(project.org, self.project_dto.org)

        self.assertEqual(project.config, {})

        permission = ProjectPermission.objects.get(project=project, user=self.user)
        self.assertEqual(permission.role, 1)

        self.sector_setup_handler.setup_sectors_in_project.assert_not_called()
        mock_send_secondary_project_to_insights.assert_not_called()

    @patch("chats.apps.projects.tasks.send_secondary_project_to_insights.delay")
    def test_create_project_with_its_principal(
        self, mock_send_secondary_project_to_insights
    ):
        """
        Test creating a project with its_principal=True in config.
        This test verifies that when we manually set its_principal=True after creation,
        subsequent projects in the same org will have its_principal=False.
        """
        mock_send_secondary_project_to_insights.return_value = MagicMock()
        mock_send_secondary_project_to_insights.delay.assert_not_called()

        project_dto = self._create_base_project_dto()
        self.use_case.create_project(project_dto)

        project = Project.objects.get(uuid=project_dto.uuid)

        project.config = {"its_principal": True}
        project.save()

        project.refresh_from_db()

        self.assertEqual(project.config, {"its_principal": True})

        second_project_dto = self._create_base_project_dto()

        self.use_case.create_project(second_project_dto)

        second_project = Project.objects.get(uuid=second_project_dto.uuid)

        self.assertEqual(second_project.config, {"its_principal": False})

        mock_send_secondary_project_to_insights.assert_called_once_with(
            str(project.uuid), str(second_project.uuid)
        )

    @patch("chats.apps.projects.tasks.send_secondary_project_to_insights.delay")
    def test_create_secondary_project(self, mock_send_secondary_project_to_insights):
        """
        Test creating a secondary project when a principal project already exists.

        This test verifies that when a project with its_principal=True exists in an org,
        any new projects created in that org will have its_principal=False in their config.
        """
        mock_send_secondary_project_to_insights.return_value = MagicMock()
        mock_send_secondary_project_to_insights.delay.assert_not_called()

        principal_project = self._create_principal_project()

        self.assertEqual(principal_project.config, {"its_principal": True})

        secondary_project_dto = self._create_base_project_dto()

        self.use_case.create_project(secondary_project_dto)

        secondary_project = Project.objects.get(uuid=secondary_project_dto.uuid)

        self.assertEqual(secondary_project.config, {"its_principal": False})

        mock_send_secondary_project_to_insights.assert_called_once_with(
            str(principal_project.uuid), str(secondary_project.uuid)
        )

        mock_send_secondary_project_to_insights.reset_mock()

        different_org_uuid = str(uuid.uuid4())
        different_org_dto = self._create_base_project_dto(org=different_org_uuid)

        self.use_case.create_project(different_org_dto)

        different_org_project = Project.objects.get(uuid=different_org_dto.uuid)

        self.assertEqual(different_org_project.config, {})

        mock_send_secondary_project_to_insights.assert_not_called()

    def test_create_template_project(self):
        """
        Test creating a template project.

        This test verifies that when is_template=True:
        1. The template_type is set correctly
        2. The sector_setup_handler is called to set up sectors
        """
        template_project_dto = self._create_base_project_dto(is_template=True)

        self.use_case.create_project(template_project_dto)

        project = Project.objects.get(uuid=template_project_dto.uuid)

        self.assertEqual(project.name, template_project_dto.name)
        self.assertTrue(project.is_template)
        self.assertEqual(project.template_type, self.template_type)

        self.sector_setup_handler.setup_sectors_in_project.assert_called_once()

        args, _ = self.sector_setup_handler.setup_sectors_in_project.call_args
        self.assertEqual(str(args[0].uuid), str(project.uuid))
        self.assertEqual(args[1], self.template_type)
        self.assertEqual(args[2].user, self.user)

    def test_create_template_project_without_template_type(self):
        """
        Test creating a template project without specifying a template type.

        This test verifies that an InvalidProjectData exception is raised when
        is_template=True but template_type_uuid is None.
        """
        template_project_dto = self._create_base_project_dto(
            is_template=True, template_type_uuid=None
        )

        with self.assertRaises(InvalidProjectData) as context:
            self.use_case.create_project(template_project_dto)

        self.assertEqual(
            str(context.exception),
            "'template_type_uuid' cannot be empty when 'is_template' is True!",
        )

    def test_create_template_project_with_nonexistent_template_type(self):
        """
        Test creating a template project with a non-existent template type.

        This test verifies that an InvalidProjectData exception is raised when
        is_template=True and template_type_uuid doesnt correspond to an existing TemplateType.
        """
        nonexistent_uuid = str(uuid.uuid4())
        template_project_dto = self._create_base_project_dto(
            is_template=True, template_type_uuid=nonexistent_uuid
        )

        with self.assertRaises(InvalidProjectData) as context:
            self.use_case.create_project(template_project_dto)

        self.assertIn(
            f"Template Type with uuid `{nonexistent_uuid}` does not exists!",
            str(context.exception),
        )

    def test_create_project_with_duplicate_uuid(self):
        """
        Test creating a project with a UUID that already exists.

        This test verifies that an InvalidProjectData exception is raised when
        attempting to create a project with a UUID that already exists.
        """
        self.use_case.create_project(self.project_dto)

        with self.assertRaises(InvalidProjectData) as context:
            self.use_case.create_project(self.project_dto)

        self.assertEqual(
            str(context.exception),
            f"The project `{self.project_dto.uuid}` already exist!",
        )

    def test_create_project_with_authorizations(self):
        """
        Test creating a project with additional user authorizations.

        This test verifies that:
        1. The creator permission is created correctly
        2. Additional permissions are created based on the authorizations in the DTO
        3. Role 3 is converted to admin role (1)
        """
        users = self._create_test_users(2)
        user2_email = users[0].email
        user3_email = users[1].email

        project_dto = self._create_base_project_dto(
            authorizations=[
                {"user_email": user2_email, "role": 2},
                {"user_email": user3_email, "role": 3},
            ],
        )

        self.use_case.create_project(project_dto)

        project = Project.objects.get(uuid=project_dto.uuid)

        self.assertEqual(project.name, project_dto.name)

        creator_permission = ProjectPermission.objects.get(
            project=project, user=self.user
        )
        self.assertEqual(creator_permission.role, 1)

        user2_permission = ProjectPermission.objects.get(project=project, user=users[0])
        self.assertEqual(user2_permission.role, 2)

        user3_permission = ProjectPermission.objects.get(project=project, user=users[1])
        self.assertEqual(user3_permission.role, 1)

    def test_config_its_principal_method(self):
        """
        Test the _config_its_principal method directly.

        This test verifies that:
        1. When no principal project exists in an org, _config_its_principal returns {}
        2. When a principal project exists in an org, _config_its_principal returns {"its_principal": False}
        3. The logic is org-specific
        """
        config = self.use_case._config_its_principal(self.project_dto)
        self.assertEqual(config, {})

        Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Principal Project",
            org=self.org_uuid,
            config={"its_principal": True},
        )

        config = self.use_case._config_its_principal(self.project_dto)
        self.assertEqual(config, {"its_principal": False})

        different_org_dto = self._create_base_project_dto(org=str(uuid.uuid4()))

        config = self.use_case._config_its_principal(different_org_dto)
        self.assertEqual(config, {})
