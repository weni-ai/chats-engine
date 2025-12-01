from unittest.mock import MagicMock
from django.test import TestCase

from chats.apps.feature_flags.services import FeatureFlagService
from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project


class TestFeatureFlagService(TestCase):
    def setUp(self):
        mock_weni_service = MagicMock()
        self.service = FeatureFlagService(feature_flags_service=mock_weni_service)
        self.user = User.objects.create(email="test@test.com")
        self.project = Project.objects.create()

    def test_get_feature_flags_list_for_user_and_project(self):
        self.service.get_feature_flags_list_for_user_and_project(
            user=self.user,
            project=self.project,
        )

        self.service.feature_flags_service.get_active_feature_flags_for_attributes.assert_called_once_with(
            {
                "userEmail": "test@test.com",
                "projectUUID": str(self.project.uuid),
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

        self.service.feature_flags_service.evaluate_feature_flag_by_attributes.assert_called_once_with(
            "example",
            {
                "projectUUID": str(self.project.uuid),
            },
        )

    def test_evaluate_feature_flag_for_user(self):
        self.service.evaluate_feature_flag(
            key="example",
            user=self.user,
        )

        self.service.feature_flags_service.evaluate_feature_flag_by_attributes.assert_called_once_with(
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

        self.service.feature_flags_service.evaluate_feature_flag_by_attributes.assert_called_once_with(
            "example",
            {
                "userEmail": "test@test.com",
                "projectUUID": str(self.project.uuid),
            },
        )

    def test_get_feature_flag_rules(self):
        self.service.feature_flags_service.get_feature_flags.return_value = {
            "exampleEmail": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {"userEmail": {"$nin": ["test@test.com"]}},
                        "force": True,
                    }
                ],
            },
        }

        rules = self.service.get_feature_flag_rules(
            key="exampleEmail",
        )

        self.service.feature_flags_service.get_feature_flags.assert_called_once_with()

        self.assertEqual(
            rules,
            [
                {
                    "id": "fr_40644z1tmdrec3rs",
                    "condition": {"userEmail": {"$nin": ["test@test.com"]}},
                    "force": True,
                }
            ],
        )
