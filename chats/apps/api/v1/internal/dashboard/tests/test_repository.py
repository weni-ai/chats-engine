import random
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import CSATRepository
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorTag
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

        total_count = sum(expected_ratings.values())

        for rating in ratings.ratings:
            self.assertEqual(rating.count, expected_ratings[rating.rating])
            self.assertEqual(
                rating.percentage,
                round((expected_ratings[rating.rating] / total_count) * 100, 2),
            )

    def test_get_csat_ratings_filter_by_queue(self):
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)

        rooms_queue1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(5)
        ]
        rooms_queue2 = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_queue1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())

        for room in rooms_queue2:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, queue=self.queue), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 5)
        self.assertEqual(rating_dict.get(4, 0), 0)

    def test_get_csat_ratings_filter_by_queues(self):
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        queue3 = Queue.objects.create(name="Test Queue 3", sector=self.sector)

        rooms_queue1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]
        rooms_queue2 = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(2)
        ]
        rooms_queue3 = [
            Room.objects.create(
                queue=queue3,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]

        for room in rooms_queue1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_queue2:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())
        for room in rooms_queue3:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, queues=[self.queue, queue2]), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 3)
        self.assertEqual(rating_dict.get(4, 0), 2)
        self.assertEqual(rating_dict.get(3, 0), 0)  # queue3 excluded

    def test_get_csat_ratings_filter_by_sector(self):
        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        queue2 = Queue.objects.create(name="Test Queue 2", sector=sector2)

        rooms_sector1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(6)
        ]
        rooms_sector2 = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]

        for room in rooms_sector1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_sector2:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, sector=[self.sector]), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 6)
        self.assertEqual(rating_dict.get(3, 0), 0)  # sector2 excluded

    def test_get_csat_ratings_filter_by_tag(self):
        tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag 2", sector=self.sector)

        rooms_tag1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]
        rooms_tag2 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_tag1:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_tag2:
            room.tags.add(tag2)
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, tag=tag1), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 4)
        self.assertEqual(rating_dict.get(4, 0), 0)  # tag2 excluded

    def test_get_csat_ratings_filter_by_tags(self):
        tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag 2", sector=self.sector)
        tag3 = SectorTag.objects.create(name="Tag 3", sector=self.sector)

        rooms_tag1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]
        rooms_tag2 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(2)
        ]
        rooms_tag3 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(5)
        ]

        for room in rooms_tag1:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_tag2:
            room.tags.add(tag2)
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())
        for room in rooms_tag3:
            room.tags.add(tag3)
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, tags=[tag1, tag2]), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 3)
        self.assertEqual(rating_dict.get(4, 0), 2)
        self.assertEqual(rating_dict.get(3, 0), 0)  # tag3 excluded

    def test_get_csat_ratings_filter_by_agent(self):
        agent1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        agent2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two"
        )

        rooms_agent1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                user=agent1,
                ended_at=timezone.now(),
            )
            for _ in range(5)
        ]
        rooms_agent2 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                user=agent2,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_agent1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_agent2:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, agent=agent1), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 5)
        self.assertEqual(rating_dict.get(4, 0), 0)  # agent2 excluded

    def test_get_csat_ratings_filter_by_start_date(self):
        now = timezone.now()
        past_date = now - timedelta(days=5)

        old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=past_date,
            )
            for _ in range(4)
        ]
        recent_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=now,
            )
            for _ in range(6)
        ]

        for room in old_rooms:
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in recent_rooms:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=room.ended_at)

        start_date = now - timedelta(days=2)
        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, start_date=start_date), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 6)
        self.assertEqual(rating_dict.get(2, 0), 0)  # old rooms excluded

    def test_get_csat_ratings_filter_by_end_date(self):
        now = timezone.now()
        past_date = now - timedelta(days=5)

        old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=past_date,
            )
            for _ in range(3)
        ]
        recent_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=now,
            )
            for _ in range(5)
        ]

        for room in old_rooms:
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in recent_rooms:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=room.ended_at)

        end_date = now - timedelta(days=1)
        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, end_date=end_date), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(2, 0), 3)
        self.assertEqual(rating_dict.get(5, 0), 0)  # recent rooms excluded

    def test_get_csat_ratings_filter_by_date_range(self):
        now = timezone.now()
        very_old_date = now - timedelta(days=10)
        old_date = now - timedelta(days=5)
        middle_date = now - timedelta(days=3)
        recent_date = now - timedelta(days=1)

        very_old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=very_old_date,
            )
            for _ in range(2)
        ]
        old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=old_date,
            )
            for _ in range(3)
        ]
        middle_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=middle_date,
            )
            for _ in range(4)
        ]
        recent_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=recent_date,
            )
            for _ in range(5)
        ]

        for room in very_old_rooms:
            CSATSurvey.objects.create(room=room, rating=1, answered_on=room.ended_at)
        for room in old_rooms:
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in middle_rooms:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=room.ended_at)
        for room in recent_rooms:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=room.ended_at)

        start_date = now - timedelta(days=6)
        end_date = now - timedelta(days=2)
        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, start_date=start_date, end_date=end_date),
            self.project,
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(2, 0), 3)  # old_rooms
        self.assertEqual(rating_dict.get(3, 0), 4)  # middle_rooms
        self.assertEqual(rating_dict.get(1, 0), 0)  # very_old excluded
        self.assertEqual(rating_dict.get(4, 0), 0)  # recent excluded

    def test_get_csat_ratings_filter_combined_queue_and_agent(self):
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        agent1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )

        rooms_filtered = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                user=agent1,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]
        rooms_wrong_queue = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                user=agent1,
                ended_at=timezone.now(),
            )
            for _ in range(2)
        ]
        rooms_wrong_agent = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_filtered:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_wrong_queue:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())
        for room in rooms_wrong_agent:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, queue=self.queue, agent=agent1),
            self.project,
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 4)  # Only matching rooms
        self.assertEqual(rating_dict.get(4, 0), 0)  # Wrong queue excluded
        self.assertEqual(rating_dict.get(3, 0), 0)  # Wrong agent excluded

    def test_get_csat_ratings_filter_combined_tag_and_date_range(self):
        tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        now = timezone.now()
        old_date = now - timedelta(days=5)
        recent_date = now - timedelta(days=1)

        rooms_tag1_old = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=old_date,
            )
            for _ in range(2)
        ]
        rooms_tag1_recent = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=recent_date,
            )
            for _ in range(5)
        ]
        rooms_no_tag_recent = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=recent_date,
            )
            for _ in range(3)
        ]

        for room in rooms_tag1_old:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in rooms_tag1_recent:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=5, answered_on=room.ended_at)
        for room in rooms_no_tag_recent:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=room.ended_at)

        start_date = now - timedelta(days=3)
        end_date = now
        ratings = self.repository.get_csat_ratings(
            Filters(
                project=self.project,
                tag=tag1,
                start_date=start_date,
                end_date=end_date,
            ),
            self.project,
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 5)  # Only tag1 + recent date
        self.assertEqual(rating_dict.get(2, 0), 0)  # Old date excluded
        self.assertEqual(rating_dict.get(4, 0), 0)  # No tag excluded

    def test_get_csat_ratings_no_surveys_matching_filters(self):
        tag = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        agent = User.objects.create(
            email="agent@test.com", first_name="Agent", last_name="One"
        )

        rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, tag=tag, agent=agent), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 0)
