import uuid
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.services import RoomsReportService
from chats.apps.sectors.models import Sector
from chats.core.cache import CacheClient


@override_settings(SEND_EMAILS=True)
class RoomsReportServiceTest(TestCase):
    def setUp(self):
        self.cache_client = CacheClient()
        self.project = Project.objects.create(name="Test Project", uuid=uuid.uuid4())
        self.service = RoomsReportService(self.project)
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=2,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Test Contact")

        # Create a timezone-aware datetime
        now = timezone.datetime(2024, 1, 15, tzinfo=timezone.get_current_timezone())
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            urn="whatsapp:1234567890",
            created_on=now,
            ended_at=now,
        )
        # Create a metric for the room
        RoomMetrics.objects.create(room=self.room, waiting_time=60)

    def tearDown(self):
        self.cache_client.delete(self.service.get_cache_key())

    def test_get_cache_key(self):
        """Test if cache key is generated correctly"""
        expected_key = f"rooms_report_{self.project.uuid}"
        self.assertEqual(self.service.get_cache_key(), expected_key)

    def test_is_generating_report(self):
        """Test if report generation status is correctly checked"""
        # Initially should be False
        self.assertFalse(self.service.is_generating_report())

        # Set cache to indicate report is being generated
        self.cache_client.set(self.service.get_cache_key(), "true", ex=300)
        self.assertTrue(self.service.is_generating_report())

        # Clear cache
        self.cache_client.delete(self.service.get_cache_key())
        self.assertFalse(self.service.is_generating_report())

    @patch("chats.apps.rooms.services.EmailMessage")
    def test_generate_report_with_rooms(self, mock_email):
        """Test report generation when rooms exist"""
        filters = {}
        recipient_email = "test@example.com"

        # Mock the email send method
        mock_email.return_value.send.return_value = None

        # Generate report
        self.service.generate_report(filters, recipient_email)

        # Verify email was sent
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args[1]["to"], [recipient_email])
        self.assertTrue(
            mock_email.call_args[1]["subject"].startswith(
                "Relatório de salas do projeto"
            )
        )

    def test_generate_report_no_rooms(self):
        """Test report generation when no rooms exist"""
        filters = {
            "created_on__gte": timezone.now() + timezone.timedelta(days=1)
        }  # Future date
        recipient_email = "test@example.com"

        # Generate report
        self.service.generate_report(filters, recipient_email)

        # Verify no email was sent
        self.assertEqual(len(mail.outbox), 0)

    @patch("chats.apps.rooms.services.EmailMessage")
    def test_generate_report_error_handling(self, mock_email):
        """Test error handling during report generation"""
        mock_email.side_effect = Exception("Test error")

        filters = {}
        recipient_email = "test@example.com"

        # Generate report
        self.service.generate_report(filters, recipient_email)

        # Verify cache was cleared after error
        self.assertFalse(self.service.is_generating_report())
