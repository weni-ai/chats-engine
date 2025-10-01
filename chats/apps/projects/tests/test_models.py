import uuid
from django.db import IntegrityError
from django.test import override_settings
from rest_framework.test import APITestCase

from chats.apps.csat.models import CSATFlowProjectConfig
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector


class ConstraintTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project_permission = ProjectPermission.objects.get(
            uuid="e416fd45-2896-43a5-bd7a-5067f03c77fa"
        )

    def test_unique_user_permission_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            ProjectPermission.objects.create(
                user=self.project_permission.user,
                project=self.project_permission.project,
            )
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_user_permission"'
            in str(context.exception)
        )


class PropertyTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project_permission = ProjectPermission.objects.get(
            uuid="e416fd45-2896-43a5-bd7a-5067f03c77fa"
        )
        self.project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(uuid="21aecf8c-0c73-4059-ba82-4343e0cc627c")

    def test_name_property(self):
        """
        Verify if the property for get project name its returning the correct value.
        """
        self.assertEqual(self.project.__str__(), self.project.name)

    def test_get_permission(self):
        """
        Verify if the property to see if user permission its returning the correct value.
        """
        permission_returned = self.project.get_permission(self.project_permission.user)
        self.assertEqual(permission_returned.user, self.project_permission.user)

    def test_admin_permissions(self):
        """
        Verify if the property to return admin permission of project its returning the correct value.
        """
        permissions_count = self.project.admin_permissions.count()
        self.assertEqual(permissions_count, 3)

    def test_random_admin(self):
        """
        Verify if the property to return admin permission of project its returning the correct value.
        """
        first_admin = self.project.admin_permissions.first()
        self.assertEqual(self.project.random_admin, first_admin)

    def test_name_property_project_permission(self):
        """
        Verify if the property for get project name its returning the correct value.
        """
        self.assertEqual(
            self.project_permission.__str__(), self.project_permission.project.name
        )

    def test_is_admin(self):
        """
        Verify if the property to see if user is admin its returning the correct value.
        """
        self.assertEqual(self.project_permission.is_admin, True)

    def test_get_project_permission(self):
        """
        Verify if the property to see if user is admin its returning the correct value.
        """
        permission_returned = self.project_permission.get_permission(
            self.project_permission.user
        )
        self.assertEqual(permission_returned.user, self.project_permission.user)

    def test_get_sectors(self):
        """
        Verify if the property to see if user is admin its returning the correct value.
        """
        sector_project = self.project.get_sectors(
            user=self.project_permission.user.email
        )

        self.assertTrue(self.sector in sector_project)

    def test_is_manager(self):
        """
        Verify if the property to see if user is admin its returning the correct value.
        """
        user_permission = self.project_permission.is_manager(sector=self.sector)
        self.assertEqual(user_permission, True)

    @override_settings(AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS=False)
    def test_has_chats_summary_when_flag_is_not_in_config_and_not_enabled_for_all_projects(
        self,
    ):
        """
        Verify that `has_chats_summary` returns `False` when the global setting
        `AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS` is `False` and the project
        config does not explicitly set `has_chats_summary`.
        """
        project = Project.objects.create(
            name="Test Project",
        )

        self.assertEqual(project.has_chats_summary, False)

    @override_settings(AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS=False)
    def test_has_chats_summary_when_flag_is_in_config_and_is_false_when_flag_is_not_enabled_for_all_projects(
        self,
    ):
        """
        Verify that `has_chats_summary` returns `False` when the global setting
        `AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS` is `False` and the project
        config explicitly sets `has_chats_summary` to `False`.
        """

        project = Project.objects.create(
            name="Test Project",
            config={"has_chats_summary": False},
        )

        self.assertEqual(project.has_chats_summary, False)

    @override_settings(AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS=False)
    def test_has_chats_summary_when_flag_is_in_config_and_is_true_when_flag_is_not_enabled_for_all_projects(
        self,
    ):
        """
        Verify that `has_chats_summary` returns `True` when the global setting
        `AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS` is `False` and the project
        config explicitly sets `has_chats_summary` to `True`.
        """
        project = Project.objects.create(
            name="Test Project",
            config={"has_chats_summary": True},
        )

        self.assertEqual(project.has_chats_summary, True)

    @override_settings(AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS=True)
    def test_has_chats_summary_when_flag_is_not_in_config_and_flag_is_enabled_for_all_projects(
        self,
    ):
        """
        Verify that `has_chats_summary` returns `True` when the global setting
        `AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS` is `True` and the project
        config does not explicitly set `has_chats_summary`.
        """
        project = Project.objects.create(
            name="Test Project",
        )

        self.assertEqual(project.has_chats_summary, True)

    @override_settings(AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS=True)
    def test_has_chats_summary_when_flag_is_in_config_and_is_true_when_flag_is_enabled_for_all_projects(
        self,
    ):
        """
        Verify that `has_chats_summary` returns `True` when the global setting
        `AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS` is `True` and the project
        config explicitly sets `has_chats_summary` to `True`.
        """
        project = Project.objects.create(
            name="Test Project",
            config={"has_chats_summary": True},
        )

        self.assertEqual(project.has_chats_summary, True)

    @override_settings(AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS=True)
    def test_has_chats_summary_when_flag_is_in_config_and_is_false_when_flag_is_enabled_for_all_projects(
        self,
    ):
        """
        Verify that `has_chats_summary` returns `True` when the global setting
        `AI_CHAT_SUMMARY_ENABLED_FOR_ALL_PROJECTS` is `True` and the project
        config explicitly sets `has_chats_summary` to `False`.
        """
        project = Project.objects.create(
            name="Test Project",
            config={"has_chats_summary": False},
        )

        self.assertEqual(project.has_chats_summary, True)

    def test_get_and_set_internal_flag(self):
        self.assertEqual(self.project.internal_flags, {})
        self.assertEqual(self.project.get_internal_flag("example"), False)

        self.project.set_internal_flag("example", True)
        self.assertEqual(self.project.internal_flags, {"example": True})
        self.assertEqual(self.project.get_internal_flag("example"), True)

    def test_is_copilot_active_when_flag_is_not_set(self):
        self.assertEqual(self.project.internal_flags, {})
        self.assertFalse(self.project.get_internal_flag("is_copilot_active"))
        self.assertFalse(self.project.is_copilot_active)

    def test_is_copilot_active_when_flag_is_set_as_false(self):
        self.project.set_internal_flag("is_copilot_active", False)
        self.assertEqual(self.project.internal_flags, {"is_copilot_active": False})
        self.assertFalse(self.project.get_internal_flag("is_copilot_active"))
        self.assertFalse(self.project.is_copilot_active)

    def test_is_copilot_active_when_flag_is_set_as_true(self):
        self.project.set_internal_flag("is_copilot_active", True)
        self.assertEqual(self.project.internal_flags, {"is_copilot_active": True})
        self.assertTrue(self.project.get_internal_flag("is_copilot_active"))
        self.assertTrue(self.project.is_copilot_active)

    def test_csat_flow_uuid_when_csat_flow_project_config_is_not_set(self):
        project = Project.objects.create(
            name="Test Project",
        )
        self.assertIsNone(project.csat_flow_uuid)

    def test_csat_flow_uuid_when_csat_flow_project_config_is_set(self):
        project = Project.objects.create(
            name="Test Project",
        )
        csat_flow_project_config = CSATFlowProjectConfig.objects.create(
            project=project,
            flow_uuid=uuid.uuid4(),
            version=1,
        )
        self.assertEqual(project.csat_flow_uuid, csat_flow_project_config.flow_uuid)
