from rest_framework.exceptions import APIException
from rest_framework.test import APITestCase

from chats.apps.accounts.models import Profile, User
from chats.apps.api.v1.users.serializers import ProfileSerializer
from chats.apps.projects.models import Project, ProjectPermission


class TestProfileSerializerGetProjectPermissionRole(APITestCase):
    def setUp(self):
        self.user = User.objects.create(email="profile@test.com")
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.project = Project.objects.create(name="Profile Project")

    def test_raises_api_exception_when_no_project_uuid(self):
        serializer = ProfileSerializer(self.profile, context={})
        with self.assertRaises(APIException):
            serializer.get_project_permission_role(self.profile)

    def test_returns_none_when_no_permission(self):
        serializer = ProfileSerializer(
            self.profile, context={"project_uuid": str(self.project.uuid)}
        )
        self.assertIsNone(serializer.get_project_permission_role(self.profile))

    def test_returns_permission_role_when_set(self):
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        serializer = ProfileSerializer(
            self.profile, context={"project_uuid": str(self.project.uuid)}
        )
        self.assertEqual(
            serializer.get_project_permission_role(self.profile),
            ProjectPermission.ROLE_ADMIN,
        )
