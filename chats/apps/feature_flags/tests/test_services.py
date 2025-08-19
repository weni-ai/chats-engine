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

        self.service.growthbook_client.get_active_feature_flags_for_attributes.assert_called_once_with(
            {
                "userEmail": "test@test.com",
                "projectUUID": self.project.uuid,
            }
        )

    def test_cannot_evaluate_feature_flag_without_attributes(self):
        with self.assertRaises(ValueError):
            self.service.evaluate_feature_flag(
                key="example",
            )

    def test_evaluate_feature_flag_for_project(self):
        self.service.evaluate_feature_flag(
            key="example",
            project=self.project,
        )

        self.service.growthbook_client.evaluate_feature_flag_by_attributes.assert_called_once_with(
            "example",
            {
                "projectUUID": self.project.uuid,
            },
        )

    def test_evaluate_feature_flag_for_user(self):
        self.service.evaluate_feature_flag(
            key="example",
            user=self.user,
        )

        self.service.growthbook_client.evaluate_feature_flag_by_attributes.assert_called_once_with(
            "example",
            {
                "userEmail": "test@test.com",
            },
        )

    def test_evaluate_feature_flag_for_user_and_project(self):
        self.service.evaluate_feature_flag(
            key="example",
            user=self.user,
            project=self.project,
        )

        self.service.growthbook_client.evaluate_feature_flag_by_attributes.assert_called_once_with(
            "example",
            {
                "userEmail": "test@test.com",
                "projectUUID": self.project.uuid,
            },
        )
