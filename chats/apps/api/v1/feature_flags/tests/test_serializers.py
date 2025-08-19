import uuid

from django.test import TestCase

from chats.apps.api.v1.feature_flags.serializers import (
    FeatureFlagsQueryParamsSerializer,
)
from chats.apps.projects.models.models import Project


class TestFeatureFlagsQueryParamsSerializer(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")

    def test_validate_project_uuid(self):
        serializer = FeatureFlagsQueryParamsSerializer(
            data={"project_uuid": self.project.uuid}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["project"], self.project)

    def test_validate_project_uuid_not_found(self):
        serializer = FeatureFlagsQueryParamsSerializer(
            data={"project_uuid": uuid.uuid4()}
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["project_uuid"], ["Project not found"])
