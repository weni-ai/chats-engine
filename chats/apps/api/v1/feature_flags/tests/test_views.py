import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.projects.tests.decorators import with_project_permission


class BaseTestFeatureFlagsViewSet(APITestCase):
    def get_active_features(self, query_params: dict) -> Response:
        url = reverse("feature_flags-list")

        return self.client.get(
            url,
            query_params,
        )


class TestFeatureFlagsViewSetAsAnonymousUser(BaseTestFeatureFlagsViewSet):
    def test_get_active_features_as_anonymous_user(self):
        response = self.get_active_features({})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestFeatureFlagsViewSetAsAuthenticatedUser(BaseTestFeatureFlagsViewSet):
    def setUp(self):
        self.user = User.objects.create(email="test@test.com")
        self.project = Project.objects.create(name="Test Project")

        self.client.force_authenticate(user=self.user)

    def test_cannot_get_active_features_without_project_uuid(
        self,
    ):
        response = self.get_active_features({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project_uuid"][0].code, "required")

    def test_cannot_get_active_features_without_permission(self):
        response = self.get_active_features({"project_uuid": self.project.uuid})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission
    @patch(
        "chats.apps.feature_flags.services.FeatureFlagService.get_feature_flags_list_for_user_and_project"
    )
    def test_get_active_features_with_valid_project_uuid(
        self,
        mock_get_feature_flags_list_for_user_and_project,
    ):
        active_features = ["feature_1", "feature_2"]
        mock_get_feature_flags_list_for_user_and_project.return_value = active_features

        response = self.get_active_features({"project_uuid": self.project.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["active_features"], active_features)
