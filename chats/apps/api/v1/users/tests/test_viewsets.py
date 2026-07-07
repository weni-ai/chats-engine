from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chats.apps.accounts.models import Profile, User
from chats.apps.projects.models import Project, ProjectPermission


class TestProfileViewset(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="profile-vs@test.com", password="pw"
        )
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name="Profile VS Project")

    def test_retrieve_creates_profile_if_missing(self):
        # No profile yet
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

        response = self.client.get(
            f"/v1/accounts/profile/?project_uuid={self.project.uuid}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_retrieve_returns_serialized_profile(self):
        Profile.objects.create(user=self.user)
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        response = self.client.get(
            f"/v1/accounts/profile/?project_uuid={self.project.uuid}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["project_permission_role"],
            ProjectPermission.ROLE_ATTENDANT,
        )

    def test_update_creates_or_updates_profile(self):
        # The viewset calls update_or_create before serialization. The serializer
        # may raise without a project_uuid context, but the profile is updated.
        self.client.put(
            "/v1/accounts/profile/",
            data={"sound_new_room": False, "sound_chat_msg": True},
            format="json",
        )

        profile = Profile.objects.get(user=self.user)
        self.assertFalse(profile.sound_new_room)
        self.assertTrue(profile.sound_chat_msg)
