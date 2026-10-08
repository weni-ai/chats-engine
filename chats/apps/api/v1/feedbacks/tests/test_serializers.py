import uuid

from django.test import TestCase

from chats.apps.api.v1.feedbacks.serializers import FeedbackSerializer
from chats.apps.projects.models import Project


class TestFeedbackSerializer(TestCase):
    def test_validate_attaches_project_when_found(self):
        project = Project.objects.create(name="Feedback Project")

        serializer = FeedbackSerializer(
            data={
                "project_uuid": str(project.uuid),
                "rating": 2,
                "comment": "ok",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["project"], project)

    def test_validate_raises_when_project_not_found(self):
        serializer = FeedbackSerializer(
            data={
                "project_uuid": str(uuid.uuid4()),
                "rating": 2,
                "comment": "ok",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("project_uuid", serializer.errors)

    def test_rating_must_be_in_range(self):
        serializer = FeedbackSerializer(
            data={
                "project_uuid": str(uuid.uuid4()),
                "rating": 10,
                "comment": "ok",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)
