from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.service import TimeMetricsService
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import MetricGoal, RoomMetrics
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TimeMetricsServiceTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
        )

        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.user = User.objects.create_user(
            email="agent@test.com", first_name="Agent", last_name="Test"
        )

        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )

        self.service = TimeMetricsService()

    def test_avg_waiting_time_with_active_rooms_in_queue(self):
        """Test average waiting time calculation for active rooms in queue"""
        now = timezone.now()
        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            added_to_queue_at=now - timedelta(hours=1)
        )
        room2 = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room2.uuid).update(
            added_to_queue_at=now - timedelta(hours=2)
        )
        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_waiting_time"], 5000)
        self.assertGreater(result["max_waiting_time"], 7000)

    def test_avg_waiting_time_with_no_rooms_in_queue(self):
        """Test waiting time returns 0 when no rooms in queue"""
        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertEqual(result["avg_waiting_time"], 0)
        self.assertEqual(result["max_waiting_time"], 0)

    def test_avg_first_response_time(self):
        """Test average first response time calculation - field doesn't exist yet"""
        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertEqual(result["avg_first_response_time"], 0)
        self.assertEqual(result["max_first_response_time"], 0)

    def test_metrics_with_date_filter(self):
        """Test metrics respect date filters"""
        now = timezone.now()
        today = now.strftime("%Y-%m-%d")
        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            added_to_queue_at=now - timedelta(minutes=10)
        )
        filters = Filters(
            start_date=today,
            end_date=today,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_waiting_time"], 500)

    def test_metrics_with_sector_filter(self):
        """Test metrics filtered by sector"""
        another_sector = Sector.objects.create(
            name="Another Sector", project=self.project, rooms_limit=10
        )
        another_queue = Queue.objects.create(
            name="Another Queue", sector=another_sector
        )

        now = timezone.now()

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            added_to_queue_at=now - timedelta(minutes=10)
        )
        room2 = Room.objects.create(
            queue=another_queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room2.uuid).update(
            added_to_queue_at=now - timedelta(minutes=20)
        )
        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=self.sector,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_waiting_time"], 500)

    def test_metrics_with_queue_filter(self):
        """Test metrics filtered by queue"""
        another_queue = Queue.objects.create(name="Another Queue", sector=self.sector)

        now = timezone.now()

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            added_to_queue_at=now - timedelta(minutes=10)
        )
        room2 = Room.objects.create(
            queue=another_queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room2.uuid).update(
            added_to_queue_at=now - timedelta(minutes=20)
        )
        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=str(self.queue.uuid),
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_waiting_time"], 500)

    def test_all_metrics_return_zero_when_no_data(self):
        """Test all metrics return 0 when there's no data"""
        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertEqual(result["avg_waiting_time"], 0)
        self.assertEqual(result["max_waiting_time"], 0)
        self.assertEqual(result["avg_first_response_time"], 0)
        self.assertEqual(result["max_first_response_time"], 0)
        self.assertEqual(result["avg_conversation_duration"], 0)
        self.assertEqual(result["max_conversation_duration"], 0)

    def test_first_response_time_with_saved_metric(self):
        """Test first response time calculation with saved metric data"""
        now = timezone.now()
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=5)
        )

        RoomMetrics.objects.create(
            room=room,
            first_response_time=300,
        )

        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertEqual(result["avg_first_response_time"], 300)
        self.assertEqual(result["max_first_response_time"], 300)

    def test_first_response_time_waiting_response(self):
        """Test first response time for rooms waiting for first response"""
        now = timezone.now()
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=10)
        )

        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_first_response_time"], 550)
        self.assertGreater(result["max_first_response_time"], 550)

    def test_conversation_duration_with_active_rooms(self):
        """Test conversation duration calculation"""
        now = timezone.now()
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=15)
        )

        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_conversation_duration"], 850)
        self.assertGreater(result["max_conversation_duration"], 850)

    def test_metrics_with_agent_filter(self):
        """Test metrics filtered by agent"""
        another_user = User.objects.create_user(
            email="agent2@test.com", first_name="Agent2", last_name="Test"
        )

        now = timezone.now()

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=10)
        )

        room2 = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=another_user,
            is_active=True,
        )
        Room.objects.filter(uuid=room2.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=20)
        )

        filters = Filters(
            start_date=None,
            end_date=None,
            agent=self.user,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertGreater(result["avg_conversation_duration"], 550)
        self.assertLess(result["avg_conversation_duration"], 700)

    def test_first_response_time_multiple_rooms_with_metrics(self):
        """Test first response time with multiple rooms having different metrics"""
        now = timezone.now()

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=5)
        )
        RoomMetrics.objects.create(room=room1, first_response_time=200)

        room2 = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room2.uuid).update(
            first_user_assigned_at=now - timedelta(minutes=10)
        )
        RoomMetrics.objects.create(room=room2, first_response_time=400)

        filters = Filters(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics(filters, self.project)

        self.assertEqual(result["avg_first_response_time"], 300)
        self.assertEqual(result["max_first_response_time"], 400)


class TimeMetricsServiceGoalsIntegrationTest(TestCase):
    """
    Verifies that `get_time_metrics` exposes the configured goals inline so
    the front can render widget alerts in the same response. Only active
    goals are included; metrics without a configured goal stay absent so
    the front does not have to special-case empty payloads.
    """

    def setUp(self):
        self.project = Project.objects.create(name="Goals Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create_user(email="agent@test.com")
        self.contact = Contact.objects.create(name="Contact", email="c@test.com")
        self.service = TimeMetricsService()

    def _filters(self, **overrides) -> Filters:
        defaults = dict(
            start_date=None,
            end_date=None,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )
        defaults.update(overrides)
        return Filters(**defaults)

    def test_response_has_no_goal_keys_when_nothing_configured(self):
        result = self.service.get_time_metrics(self._filters(), self.project)

        self.assertNotIn("waiting_time_goal", result)
        self.assertNotIn("first_response_time_goal", result)
        self.assertNotIn("conversation_duration_goal", result)

    def test_inactive_goal_is_omitted(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            is_active=False,
        )

        result = self.service.get_time_metrics(self._filters(), self.project)

        self.assertNotIn("waiting_time_goal", result)

    def test_active_goal_appears_with_threshold_value(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_MINUTE,
            rooms_threshold_count=5,
        )

        result = self.service.get_time_metrics(self._filters(), self.project)

        goal = result["waiting_time_goal"]
        self.assertEqual(goal["threshold_seconds"], 300)
        self.assertEqual(goal["threshold_value"], 5)
        self.assertEqual(goal["unit"], MetricGoal.UNIT_MINUTE)
        self.assertEqual(goal["breached_rooms_count"], 0)
        self.assertFalse(goal["is_breached"])

    def test_breach_count_reflects_real_rooms(self):
        now = timezone.now()
        # 3 rooms over the 300s threshold.
        for i in range(3):
            room = Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(
                    name=f"c-{i}", email=f"c{i}@test.com"
                ),
                user=None,
                is_active=True,
            )
            Room.objects.filter(uuid=room.uuid).update(
                added_to_queue_at=now - timedelta(seconds=400)
            )

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=5,
        )

        result = self.service.get_time_metrics(self._filters(), self.project)

        goal = result["waiting_time_goal"]
        self.assertEqual(goal["breached_rooms_count"], 3)
        # Below `rooms_threshold_count` (5), so the goal is not breached.
        self.assertFalse(goal["is_breached"])

    def test_is_breached_when_count_meets_threshold(self):
        now = timezone.now()
        for i in range(5):
            room = Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(
                    name=f"c-{i}", email=f"c{i}@test.com"
                ),
                user=None,
                is_active=True,
            )
            Room.objects.filter(uuid=room.uuid).update(
                added_to_queue_at=now - timedelta(seconds=400)
            )

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=5,
        )

        result = self.service.get_time_metrics(self._filters(), self.project)

        goal = result["waiting_time_goal"]
        self.assertEqual(goal["breached_rooms_count"], 5)
        self.assertTrue(goal["is_breached"])
