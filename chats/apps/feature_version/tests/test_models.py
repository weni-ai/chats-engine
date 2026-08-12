from django.test import TestCase

from chats.apps.feature_version.models import IntegratedFeature
from chats.apps.projects.models.models import Project


class IntegratedFeatureModelTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Feature Project")

    def test_create_integrated_feature_with_version_payload(self):
        feature = IntegratedFeature.objects.create(
            project=self.project,
            feature="feature-uuid-123",
            current_version={"version": "1.0.0", "enabled": True},
        )

        self.assertEqual(feature.project, self.project)
        self.assertEqual(feature.feature, "feature-uuid-123")
        self.assertEqual(
            feature.current_version,
            {"version": "1.0.0", "enabled": True},
        )
        self.assertIsNotNone(feature.uuid)
        self.assertEqual(self.project.feature_versions.count(), 1)

    def test_current_version_can_be_null(self):
        feature = IntegratedFeature.objects.create(
            project=self.project,
            feature="another-feature",
            current_version=None,
        )

        self.assertIsNone(feature.current_version)

    def test_deleting_project_cascades_to_integrated_feature(self):
        IntegratedFeature.objects.create(
            project=self.project,
            feature="feature-to-delete",
            current_version={"version": "2.0.0"},
        )

        self.project.delete()

        self.assertEqual(IntegratedFeature.objects.count(), 0)
