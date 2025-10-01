from datetime import timedelta
from django.utils import timezone
from django.test import TestCase

from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.service import TimeMetricsService
from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TimeMetricsServiceTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            timezone="UTC"
        )
        
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
        )
        
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector
        )
        
        self.user = User.objects.create_user(
            email="agent@test.com",
            first_name="Agent",
            last_name="Test"
        )
        
        self.contact = Contact.objects.create(
            name="Test Contact",
            email="contact@test.com"
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
            is_weni_admin=False
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
            is_weni_admin=False
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertEqual(result["avg_first_response_time"], 0)
        self.assertEqual(result["max_first_response_time"], 0)

    def test_avg_conversation_duration_with_active_rooms(self):
        """Test conversation duration with active rooms"""
        now = timezone.now()
        
        active_room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=active_room.uuid).update(
            user_assigned_at=now - timedelta(minutes=30)
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertGreater(result["avg_conversation_duration"], 1700)

    def test_avg_conversation_duration_with_closed_rooms(self):
        """Test conversation duration with closed rooms"""
        now = timezone.now()
        
        closed_room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        
        Room.objects.filter(uuid=closed_room.uuid).update(
            user_assigned_at=now - timedelta(minutes=20),
            is_active=False,
            ended_at=now - timedelta(minutes=10)
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertEqual(result["avg_conversation_duration"], 600)

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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertGreater(result["avg_waiting_time"], 500)

    def test_metrics_with_agent_filter(self):
        """Test metrics filtered by specific agent"""
        now = timezone.now()
        another_user = User.objects.create_user(email="agent2@test.com")
        
        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room1.uuid).update(
            user_assigned_at=now - timedelta(minutes=5)
        )
        
        room2 = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=another_user,
            is_active=True,
        )
        Room.objects.filter(uuid=room2.uuid).update(
            user_assigned_at=now - timedelta(minutes=10)
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertGreater(result["avg_conversation_duration"], 290)

    def test_metrics_with_sector_filter(self):
        """Test metrics filtered by sector"""
        another_sector = Sector.objects.create(
            name="Another Sector",
            project=self.project,
            rooms_limit=10
        )
        another_queue = Queue.objects.create(
            name="Another Queue",
            sector=another_sector
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertGreater(result["avg_waiting_time"], 500)

    def test_metrics_with_queue_filter(self):
        """Test metrics filtered by queue"""
        another_queue = Queue.objects.create(
            name="Another Queue",
            sector=self.sector
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
            sector=None,
            tag=None,
            queue=str(self.queue.uuid),
            user_request=None,
            project=self.project,
            is_weni_admin=False
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertEqual(result["avg_waiting_time"], 0)
        self.assertEqual(result["max_waiting_time"], 0)
        self.assertEqual(result["avg_first_response_time"], 0)
        self.assertEqual(result["max_first_response_time"], 0)
        self.assertEqual(result["avg_conversation_duration"], 0)
        self.assertEqual(result["max_conversation_duration"], 0)

    def test_metrics_without_date_filter_only_today(self):
        """Test that without date filter, only today's data is considered"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today_start - timedelta(days=1)
        
        old_room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
            created_on=yesterday,
        )
        Room.objects.filter(uuid=old_room.uuid).update(
            user_assigned_at=yesterday - timedelta(seconds=100),
            is_active=False,
            ended_at=yesterday
        )
        
        today_room = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=today_room.uuid).update(
            user_assigned_at=now - timedelta(seconds=200),
            is_active=False,
            ended_at=now
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
            is_weni_admin=False
        )
        
        result = self.service.get_time_metrics(filters, self.project)
        
        self.assertEqual(result["avg_conversation_duration"], 200)