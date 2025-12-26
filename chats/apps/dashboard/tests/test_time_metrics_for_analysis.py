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
from chats.apps.sectors.models import Sector, SectorTag


class GetTimeMetricsForAnalysisTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector", project=self.project, rooms_limit=10
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create_user(
            email="agent@test.com", first_name="Agent", last_name="Test"
        )
        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )
        self.service = TimeMetricsService()
        self.now = timezone.now()
        self.today = self.now.strftime("%Y-%m-%d")
        self.tomorrow = (self.now + timedelta(days=1)).strftime("%Y-%m-%d")

    def test_get_time_metrics_for_analysis_requires_dates(self):
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

        with self.assertRaises(ValueError) as context:
            self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertIn("required", str(context.exception).lower())

    def test_get_time_metrics_for_analysis_with_no_rooms(self):
        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 0)
        self.assertEqual(result["avg_waiting_time"], 0)
        self.assertEqual(result["max_first_response_time"], 0)
        self.assertEqual(result["avg_first_response_time"], 0)
        self.assertEqual(result["max_conversation_duration"], 0)
        self.assertEqual(result["avg_conversation_duration"], 0)
        self.assertEqual(result["avg_message_response_time"], 0)

    def test_get_time_metrics_for_analysis_with_closed_rooms(self):
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        room.is_active = False
        room.save()

        Room.objects.filter(uuid=room.uuid).update(
            ended_at=self.now,
            first_user_assigned_at=self.now - timedelta(hours=1),
        )
        RoomMetrics.objects.create(
            room=room,
            waiting_time=300,
            first_response_time=60,
            interaction_time=3600,
            message_response_time=30,
        )

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 300)
        self.assertEqual(result["avg_waiting_time"], 300)
        self.assertEqual(result["max_first_response_time"], 60)
        self.assertEqual(result["avg_first_response_time"], 60)

    def test_get_time_metrics_for_analysis_filters_by_agent(self):
        other_user = User.objects.create_user(
            email="agent2@test.com", first_name="Agent2", last_name="Test"
        )

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        room1.is_active = False
        room1.save()
        Room.objects.filter(uuid=room1.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room1, waiting_time=100, first_response_time=50)

        room2 = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=other_user,
            is_active=True,
        )
        room2.is_active = False
        room2.save()
        Room.objects.filter(uuid=room2.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(
            room=room2, waiting_time=200, first_response_time=100
        )

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=self.user,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)
        self.assertEqual(result["avg_waiting_time"], 100)

    def test_get_time_metrics_for_analysis_filters_by_sector(self):
        other_sector = Sector.objects.create(
            name="Other Sector", project=self.project, rooms_limit=10
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        room1.is_active = False
        room1.save()
        Room.objects.filter(uuid=room1.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room1, waiting_time=100)

        room2 = Room.objects.create(
            queue=other_queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=self.user,
            is_active=True,
        )
        room2.is_active = False
        room2.save()
        Room.objects.filter(uuid=room2.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room2, waiting_time=200)

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=self.sector,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)
        self.assertEqual(result["avg_waiting_time"], 100)

    def test_get_time_metrics_for_analysis_filters_by_queue(self):
        other_queue = Queue.objects.create(name="Other Queue", sector=self.sector)

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        room1.is_active = False
        room1.save()
        Room.objects.filter(uuid=room1.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room1, waiting_time=100)

        room2 = Room.objects.create(
            queue=other_queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=self.user,
            is_active=True,
        )
        room2.is_active = False
        room2.save()
        Room.objects.filter(uuid=room2.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room2, waiting_time=200)

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=None,
            queue=str(self.queue.uuid),
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)
        self.assertEqual(result["avg_waiting_time"], 100)

    def test_get_time_metrics_for_analysis_filters_by_tag(self):
        tag = SectorTag.objects.create(name="Test Tag", sector=self.sector)

        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        room1.is_active = False
        room1.save()
        Room.objects.filter(uuid=room1.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        room1.tags.add(tag)
        RoomMetrics.objects.create(room=room1, waiting_time=100)

        room2 = Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(name="Contact 2", email="contact2@test.com"),
            user=self.user,
            is_active=True,
        )
        room2.is_active = False
        room2.save()
        Room.objects.filter(uuid=room2.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room2, waiting_time=200)

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=str(tag.uuid),
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 100)
        self.assertEqual(result["avg_waiting_time"], 100)

    def test_get_time_metrics_for_analysis_calculates_averages(self):
        for i in range(3):
            contact = Contact.objects.create(
                name=f"Contact {i}", email=f"contact{i}@test.com"
            )
            room = Room.objects.create(
                queue=self.queue,
                contact=contact,
                user=self.user,
                is_active=True,
            )
            room.is_active = False
            room.save()
            Room.objects.filter(uuid=room.uuid).update(
                ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
            )
            RoomMetrics.objects.create(
                room=room,
                waiting_time=(i + 1) * 100,
                first_response_time=(i + 1) * 10,
            )

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 300)
        self.assertEqual(result["avg_waiting_time"], 200)
        self.assertEqual(result["max_first_response_time"], 30)
        self.assertEqual(result["avg_first_response_time"], 20)

    def test_get_time_metrics_for_analysis_message_response_time(self):
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        room.is_active = False
        room.save()
        Room.objects.filter(uuid=room.uuid).update(
            ended_at=self.now, first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room, message_response_time=45)

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["avg_message_response_time"], 45)

    def test_get_time_metrics_for_analysis_excludes_active_rooms(self):
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room.uuid).update(
            first_user_assigned_at=self.now - timedelta(hours=1)
        )
        RoomMetrics.objects.create(room=room, waiting_time=100)

        filters = Filters(
            start_date=self.today,
            end_date=self.tomorrow,
            agent=None,
            sector=None,
            tag=None,
            queue=None,
            user_request=None,
            project=self.project,
            is_weni_admin=False,
        )

        result = self.service.get_time_metrics_for_analysis(filters, self.project)

        self.assertEqual(result["max_waiting_time"], 0)
        self.assertEqual(result["avg_waiting_time"], 0)
