from django.test import TestCase

from chats.apps.feature_flags.services import FeatureFlagService
from chats.apps.feature_flags.integrations.growthbook.tests.mock import (
    MockGrowthbookClient,
)
from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project


class TestFeatureFlagService(TestCase):
    def setUp(self):
        self.service = FeatureFlagService(growthbook_client=MockGrowthbookClient())
        self.user = User.objects.create(email="test@test.com")
        self.project = Project.objects.create()

    def test_get_feature_flags_list_for_user_and_project(self):
        self.service.get_feature_flags_list_for_user_and_project(
            user=self.user,
            project=self.project,
        )

        self.service.growthbook_client.evaluate_features_by_attributes.assert_called_once_with(
            {
                "userEmail": "test@test.com",
                "projectUUID": self.project.uuid,
            }
        )
