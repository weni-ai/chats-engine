from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from chats.apps.csat.models import CSATSurvey
from chats.apps.rooms.models import Room
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.contacts.models import Contact


class CSATSurveyModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Test Contact")
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, project_uuid=self.project.uuid
        )

    def test_create_csat_survey(self):
        csat_survey = CSATSurvey.objects.create(
            room=self.room,
            rating=5,
            comment="Great service!",
            answered_on=timezone.now(),
        )
        self.assertEqual(csat_survey.room, self.room)
        self.assertEqual(csat_survey.rating, 5)
        self.assertEqual(csat_survey.comment, "Great service!")

    def test_create_csat_survey_with_invalid_rating(self):
        with self.assertRaises(ValidationError) as context:
            CSATSurvey.objects.create(
                room=self.room,
                rating=6,
                comment="Great service!",
                answered_on=timezone.now(),
            )

        self.assertIn("rating", context.exception.__dict__["error_dict"])

        with self.assertRaises(ValidationError) as context:
            CSATSurvey.objects.create(
                room=self.room, rating=0, comment="Terrible service!"
            )

        self.assertIn("rating", context.exception.__dict__["error_dict"])

    def test_create_csat_survey_without_comment(self):
        csat_survey = CSATSurvey.objects.create(
            room=self.room, rating=5, answered_on=timezone.now()
        )
        self.assertIsNone(csat_survey.comment)
