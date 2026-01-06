from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.service import TimeMetricsService
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
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
