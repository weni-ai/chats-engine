import random
from django.test import TestCase
from django.utils import timezone

from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import CSATRepository
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey


class CSATRepositoryTest(TestCase):
    def setUp(self):
        self.repository = CSATRepository()

        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def test_get_csat_ratings(self):
        rooms = [
            Room.objects.create(queue=self.queue, project_uuid=self.project.uuid)
            for _ in range(10)
        ]

        expected_ratings = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
        }

        for room in rooms:
            rating = random.randint(1, 5)
            CSATSurvey.objects.create(
                room=room, rating=rating, answered_on=timezone.now()
            )
            expected_ratings[rating] += 1

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project), self.project
        )

        for rating in ratings:
            self.assertEqual(rating.count, expected_ratings[rating.rating])
