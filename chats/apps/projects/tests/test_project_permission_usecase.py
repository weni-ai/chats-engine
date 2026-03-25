import uuid

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.usecases.exceptions import InvalidProjectPermission
from chats.apps.projects.usecases.permission_creation import (
    ProjectPermissionCreationUseCase,
    ProjectPermissionDTO,
)


class TestProjectPermissionCreationUseCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Test Project",
        )
        self.user, _ = User.objects.get_or_create(email="test@example.com")
        self.config = {
            "project": str(self.project.uuid),
            "role": 2,
        }
        self.use_case = ProjectPermissionCreationUseCase(config=self.config)

    def _make_dto(self, **kwargs):
        defaults = {
            "project": str(self.project.uuid),
            "user": self.user.email,
            "role": "2",
        }
        defaults.update(kwargs)
        return ProjectPermissionDTO(**defaults)

    def _create_test_users(self, count=1):
        users = []
        for i in range(count):
            email = f"user{i+1}@example.com"
            user, _ = User.objects.get_or_create(email=email)
            users.append(user)
        return users

    # --- role_mapping ---

    def test_role_mapping_returns_admin_for_role_3(self):
        use_case = ProjectPermissionCreationUseCase(config={"role": 3})
        self.assertEqual(use_case.role_mapping(), 1)

    def test_role_mapping_returns_attendant_for_other_roles(self):
        for role in [0, 1, 2, 4, 5]:
            use_case = ProjectPermissionCreationUseCase(config={"role": role})
            self.assertEqual(use_case.role_mapping(), 2, f"Expected 2 for role={role}")

    # --- get_project ---

    def test_get_project_returns_correct_project(self):
        project = self.use_case.get_project()
        self.assertEqual(str(project.uuid), str(self.project.uuid))

    def test_get_project_raises_for_nonexistent_uuid(self):
        use_case = ProjectPermissionCreationUseCase(
            config={"project": str(uuid.uuid4())}
        )
        with self.assertRaises(Project.DoesNotExist):
            use_case.get_project()

    # --- get_or_create_user_by_email ---

    def test_get_or_create_user_returns_existing_user(self):
        user, created = self.use_case.get_or_create_user_by_email(self.user.email)
        self.assertEqual(user, self.user)
        self.assertFalse(created)

    def test_get_or_create_user_creates_new_user(self):
        new_email = "newuser@example.com"
        user, created = self.use_case.get_or_create_user_by_email(new_email)
        self.assertEqual(user.email, new_email)
        self.assertTrue(created)

    # --- create_permission ---

    def test_create_permission_creates_new_permission(self):
        dto = self._make_dto()
        self.use_case.create_permission(dto)

        permission = ProjectPermission.all_objects.get(
            project=self.project, user=self.user
        )
        self.assertEqual(permission.role, 2)
        self.assertFalse(permission.is_deleted)

    def test_create_permission_creates_user_if_not_exists(self):
        dto = self._make_dto(user="brand_new@example.com")
        self.use_case.create_permission(dto)

        self.assertTrue(User.objects.filter(email="brand_new@example.com").exists())
        new_user = User.objects.get(email="brand_new@example.com")
        permission = ProjectPermission.all_objects.get(
            project=self.project, user=new_user
        )
        self.assertEqual(permission.role, 2)

    def test_create_permission_with_role_3_maps_to_admin(self):
        use_case = ProjectPermissionCreationUseCase(
            config={"project": str(self.project.uuid), "role": 3}
        )
        dto = self._make_dto()
        use_case.create_permission(dto)

        permission = ProjectPermission.all_objects.get(
            project=self.project, user=self.user
        )
        self.assertEqual(permission.role, ProjectPermission.ROLE_ADMIN)

    def test_create_permission_reactivates_soft_deleted_permission(self):
        """When a soft-deleted permission exists for the same user+project,
        create_permission should find it via all_objects and update it."""
        soft_perm = ProjectPermission.all_objects.create(
            project=self.project,
            user=self.user,
            role=1,
            is_deleted=True,
        )

        dto = self._make_dto()
        self.use_case.create_permission(dto)

        perms = ProjectPermission.all_objects.filter(
            project=self.project, user=self.user
        )
        self.assertEqual(perms.count(), 1)

        perm = perms.first()
        self.assertEqual(perm.uuid, soft_perm.uuid)
        self.assertEqual(perm.role, 2)

    def test_create_permission_updates_existing_active_permission(self):
        """When an active permission already exists, create_permission should
        update its role instead of creating a duplicate."""
        ProjectPermission.all_objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
            is_deleted=False,
        )

        dto = self._make_dto()
        self.use_case.create_permission(dto)

        perms = ProjectPermission.all_objects.filter(
            project=self.project, user=self.user
        )
        self.assertEqual(perms.count(), 1)
        self.assertEqual(perms.first().role, ProjectPermission.ROLE_ATTENDANT)

    def test_create_permission_is_not_soft_deleted(self):
        dto = self._make_dto()
        self.use_case.create_permission(dto)

        perm = ProjectPermission.all_objects.get(project=self.project, user=self.user)
        self.assertFalse(perm.is_deleted)

    # --- edit_permission ---

    def test_edit_permission_updates_all_fields(self):
        permission = ProjectPermission.all_objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        another_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Another Project",
        )
        another_user = self._create_test_users(1)[0]

        self.use_case.edit_permission(
            permission, another_user, ProjectPermission.ROLE_ATTENDANT, another_project
        )

        permission.refresh_from_db()
        self.assertEqual(str(permission.project_id), str(another_project.pk))
        self.assertEqual(permission.user_id, another_user.email)
        self.assertEqual(permission.role, ProjectPermission.ROLE_ATTENDANT)

    # --- delete_permission ---

    def test_delete_permission_soft_deletes_existing_permission(self):
        ProjectPermission.all_objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
            is_deleted=False,
        )

        dto = self._make_dto(
            project=str(self.project.uuid),
            user=self.user.email,
        )
        self.use_case.delete_permission(dto)

        self.assertFalse(
            ProjectPermission.objects.filter(
                project=self.project, user=self.user
            ).exists()
        )
        self.assertTrue(
            ProjectPermission.all_objects.filter(
                project=self.project, user=self.user
            ).exists()
        )

    def test_delete_permission_raises_for_nonexistent_permission(self):
        dto = self._make_dto(
            project=str(self.project.uuid),
            user=self.user.email,
        )
        with self.assertRaises(InvalidProjectPermission):
            self.use_case.delete_permission(dto)

    def test_delete_permission_raises_for_already_soft_deleted(self):
        """Trying to delete a permission that is already soft-deleted should
        raise InvalidProjectPermission since it's invisible to the default manager."""
        ProjectPermission.all_objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
            is_deleted=True,
        )

        dto = self._make_dto(
            project=str(self.project.uuid),
            user=self.user.email,
        )
        with self.assertRaises(InvalidProjectPermission):
            self.use_case.delete_permission(dto)
