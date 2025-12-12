from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.service import TimeMetricsService
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorTag


class TestGetTimeMetricsForAnalysis(TestCase):
    def setUp(self):
        self.service = TimeMetricsService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@test.com")
        self.tag = SectorTag.objects.create(name="Test Tag", sector=self.sector)

        self.now = timezone.now()
        self.start_date = self.now - timedelta(days=7)
        self.end_date = self.now

    def _create_closed_room_with_metrics(
        self,
        waiting_time=0,
        first_response_time=0,
        interaction_time=0,
        message_response_time=0,
        user=None,
        queue=None,
        tags=None,
        ended_at=None,
    ):
        room = Room.objects.create(
            queue=queue or self.queue,
            user=user,
            is_active=False,
            ended_at=ended_at or self.now - timedelta(hours=1),
            first_user_assigned_at=self.now - timedelta(hours=2) if user else None,
        )
        metric, _ = RoomMetrics.objects.get_or_create(room=room)
        metric.waiting_time = waiting_time
        metric.first_response_time = first_response_time
        metric.interaction_time = interaction_time
        metric.message_response_time = message_response_time
        metric.save()
        if tags:
            room.tags.set(tags)
        return room

    def test_raises_value_error_when_dates_are_missing(self):
        filters = Filters()
        with self.assertRaises(ValueError) as context:
            self.service.get_time_metrics_for_analysis(filters, self.project)
        self.assertEqual(str(context.exception), "Start date and end date are required")

    def test_returns_zeros_when_no_rooms_exist(self):
        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)
        expected = {
            "max_waiting_time": 0,
            "avg_waiting_time": 0,
            "max_first_response_time": 0,
            "avg_first_response_time": 0,
            "max_conversation_duration": 0,
            "avg_conversation_duration": 0,
            "avg_message_response_time": 0,
        }
        self.assertEqual(result, expected)

    def test_calculates_waiting_time_metrics(self):
        self._create_closed_room_with_metrics(waiting_time=100)
        self._create_closed_room_with_metrics(waiting_time=200)
        self._create_closed_room_with_metrics(waiting_time=300)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 300)
        self.assertEqual(result["avg_waiting_time"], 200)

    def test_calculates_first_response_time_metrics(self):
        self._create_closed_room_with_metrics(first_response_time=50)
        self._create_closed_room_with_metrics(first_response_time=100)
        self._create_closed_room_with_metrics(first_response_time=150)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_first_response_time"], 150)
        self.assertEqual(result["avg_first_response_time"], 100)

    def test_calculates_conversation_duration_metrics(self):
        self._create_closed_room_with_metrics(
            interaction_time=60, user=self.user
        )
        self._create_closed_room_with_metrics(
            interaction_time=120, user=self.user
        )
        self._create_closed_room_with_metrics(
            interaction_time=180, user=self.user
        )

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_conversation_duration"], 180)
        self.assertEqual(result["avg_conversation_duration"], 120)

    def test_calculates_message_response_time_metrics(self):
        self._create_closed_room_with_metrics(message_response_time=30)
        self._create_closed_room_with_metrics(message_response_time=60)
        self._create_closed_room_with_metrics(message_response_time=90)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["avg_message_response_time"], 60)

    def test_filters_by_agent(self):
        other_user = User.objects.create(email="other@test.com")
        self._create_closed_room_with_metrics(waiting_time=100, user=self.user)
        self._create_closed_room_with_metrics(waiting_time=200, user=other_user)

        filters = Filters(
            start_date=self.start_date, end_date=self.end_date, agent=self.user
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)
        self.assertEqual(result["avg_waiting_time"], 100)

    def test_filters_by_sector(self):
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)

        self._create_closed_room_with_metrics(waiting_time=100, queue=self.queue)
        self._create_closed_room_with_metrics(waiting_time=500, queue=other_queue)

        filters = Filters(
            start_date=self.start_date, end_date=self.end_date, sector=self.sector
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)

    def test_filters_by_sector_list(self):
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)

        self._create_closed_room_with_metrics(waiting_time=100, queue=self.queue)
        self._create_closed_room_with_metrics(waiting_time=200, queue=other_queue)

        filters = Filters(
            start_date=self.start_date,
            end_date=self.end_date,
            sector=[self.sector, other_sector],
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 200)
        self.assertEqual(result["avg_waiting_time"], 150)

    def test_filters_by_queue(self):
        other_queue = Queue.objects.create(name="Other Queue", sector=self.sector)

        self._create_closed_room_with_metrics(waiting_time=100, queue=self.queue)
        self._create_closed_room_with_metrics(waiting_time=500, queue=other_queue)

        filters = Filters(
            start_date=self.start_date, end_date=self.end_date, queue=self.queue.uuid
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)

    def test_filters_by_queue_list(self):
        other_queue = Queue.objects.create(name="Other Queue", sector=self.sector)

        self._create_closed_room_with_metrics(waiting_time=100, queue=self.queue)
        self._create_closed_room_with_metrics(waiting_time=200, queue=other_queue)

        filters = Filters(
            start_date=self.start_date,
            end_date=self.end_date,
            queue=[self.queue.uuid, other_queue.uuid],
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 200)

    def test_filters_by_tag(self):
        other_tag = SectorTag.objects.create(name="Other Tag", sector=self.sector)

        self._create_closed_room_with_metrics(waiting_time=100, tags=[self.tag])
        self._create_closed_room_with_metrics(waiting_time=500, tags=[other_tag])

        filters = Filters(
            start_date=self.start_date, end_date=self.end_date, tag=self.tag.uuid
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)

    def test_filters_by_tag_list(self):
        other_tag = SectorTag.objects.create(name="Other Tag", sector=self.sector)

        self._create_closed_room_with_metrics(waiting_time=100, tags=[self.tag])
        self._create_closed_room_with_metrics(waiting_time=200, tags=[other_tag])

        filters = Filters(
            start_date=self.start_date,
            end_date=self.end_date,
            tag=[self.tag.uuid, other_tag.uuid],
        )
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 200)

    def test_excludes_active_rooms(self):
        Room.objects.create(queue=self.queue, is_active=True)
        self._create_closed_room_with_metrics(waiting_time=100)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)

    def test_excludes_rooms_outside_date_range(self):
        self._create_closed_room_with_metrics(
            waiting_time=100, ended_at=self.now - timedelta(days=1)
        )
        self._create_closed_room_with_metrics(
            waiting_time=500, ended_at=self.now - timedelta(days=30)
        )

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)

    def test_ignores_rooms_without_first_user_assigned_for_conversation_duration(self):
        self._create_closed_room_with_metrics(interaction_time=100, user=None)
        self._create_closed_room_with_metrics(interaction_time=200, user=self.user)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_conversation_duration"], 200)
        self.assertEqual(result["avg_conversation_duration"], 200)

    def test_ignores_zero_message_response_times(self):
        self._create_closed_room_with_metrics(message_response_time=0)
        self._create_closed_room_with_metrics(message_response_time=100)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["avg_message_response_time"], 100)

    def test_excludes_rooms_from_other_projects(self):
        other_project = Project.objects.create(name="Other Project")
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)

        self._create_closed_room_with_metrics(waiting_time=100, queue=self.queue)
        self._create_closed_room_with_metrics(waiting_time=999, queue=other_queue)

        filters = Filters(start_date=self.start_date, end_date=self.end_date)
        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)
