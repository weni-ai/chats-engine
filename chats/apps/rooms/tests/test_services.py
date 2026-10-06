import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.services import RoomsReportService, can_retrieve, requeue_agent_rooms
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.core.cache import CacheClient


User = get_user_model()


class RequeueAgentRoomsTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Requeue Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Client")
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")

    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_rooms_are_unassigned_from_user(self, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        room.refresh_from_db()
        self.assertIsNone(room.user)

    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_inactive_rooms_are_excluded_by_filter(self, mock_routing):
        inactive_room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=False
        )
        active_room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        rooms = Room.objects.filter(user=self.agent, is_active=True)
        self.assertEqual(rooms.count(), 1)
        requeue_agent_rooms(rooms)
        active_room.refresh_from_db()
        inactive_room.refresh_from_db()
        self.assertIsNone(active_room.user)
        self.assertEqual(inactive_room.user, self.agent)

    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_rooms_without_user_are_skipped(self, mock_routing):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=None, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        room.refresh_from_db()
        self.assertIsNone(room.user)
        mock_routing.assert_not_called()

    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_queue_routing_is_triggered_for_affected_queues(self, mock_routing):
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(user=self.agent, is_active=True))
        mock_routing.assert_called_once_with(self.queue)

    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_multiple_rooms_across_queues(self, mock_routing):
        queue_2 = Queue.objects.create(name="Queue 2", sector=self.sector)
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        Room.objects.create(
            queue=queue_2, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(user=self.agent, is_active=True))
        self.assertEqual(mock_routing.call_count, 2)
        called_queues = {call.args[0] for call in mock_routing.call_args_list}
        self.assertEqual(called_queues, {self.queue, queue_2})

    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_empty_queryset_does_nothing(self, mock_routing):
        requeue_agent_rooms(Room.objects.none())
        mock_routing.assert_not_called()

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_feedback_message_is_created_on_requeue(self, mock_routing, mock_feedback):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        mock_feedback.assert_called_once()

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_no_feedback_for_rooms_without_user(self, mock_routing, mock_feedback):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=None, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        mock_feedback.assert_not_called()

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_feedback_action_is_requeue(self, mock_routing, mock_feedback):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        _, feedback_arg = mock_feedback.call_args.args
        self.assertEqual(feedback_arg["action"], "requeue")

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_feedback_from_is_agent_to_is_queue(self, mock_routing, mock_feedback):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        _, feedback_arg = mock_feedback.call_args.args
        self.assertEqual(feedback_arg["from"]["type"], "user")
        self.assertEqual(feedback_arg["from"]["email"], self.agent.email)
        self.assertEqual(feedback_arg["to"]["type"], "queue")
        self.assertEqual(feedback_arg["to"]["name"], self.queue.name)

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_feedback_uses_room_transfer_method(self, mock_routing, mock_feedback):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        method_kwarg = mock_feedback.call_args.kwargs["method"]
        self.assertEqual(method_kwarg, RoomFeedbackMethods.ROOM_TRANSFER)

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_transfer_history_is_updated_on_requeue(self, mock_routing, mock_feedback):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(uuid=room.uuid))
        room.refresh_from_db()
        self.assertEqual(len(room.full_transfer_history), 1)
        entry = room.full_transfer_history[0]
        self.assertEqual(entry["action"], "requeue")
        self.assertEqual(entry["from"]["email"], self.agent.email)
        self.assertEqual(entry["to"]["name"], self.queue.name)

    @patch("chats.apps.rooms.services.create_room_feedback_message")
    @patch("chats.apps.rooms.services.start_queue_priority_routing")
    def test_feedback_is_created_for_each_room_with_user(self, mock_routing, mock_feedback):
        contact_2 = Contact.objects.create(name="Client 2")
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        Room.objects.create(
            queue=self.queue, contact=contact_2, user=self.agent, is_active=True
        )
        requeue_agent_rooms(Room.objects.filter(user=self.agent, is_active=True))
        self.assertEqual(mock_feedback.call_count, 2)


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

    @patch("chats.apps.rooms.services.EmailMultiAlternatives")
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

    @patch("chats.apps.rooms.services.EmailMultiAlternatives")
    def test_generate_report_error_handling(self, mock_email):
        """Test error handling during report generation"""
        mock_email.side_effect = Exception("Test error")

        filters = {}
        recipient_email = "test@example.com"

        # Generate report
        self.service.generate_report(filters, recipient_email)

        # Verify cache was cleared after error
        self.assertFalse(self.service.is_generating_report())

    @patch("chats.apps.rooms.services.EmailMultiAlternatives")
    def test_generate_report_error_notification_success(self, mock_email):
        """Ensure error notification email is sent when initial send fails"""
        notification_email = MagicMock()
        notification_email.send.return_value = None
        mock_email.side_effect = [Exception("primary send failure"), notification_email]

        self.service.generate_report({}, "ops@example.com")

        notification_email.attach_alternative.assert_called_once()
        notification_email.send.assert_called_once_with(fail_silently=False)
        self.assertFalse(self.service.is_generating_report())


class CanRetrieveServiceTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Retrieve Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=1,
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Client")
        self.project_uuid = str(self.project.uuid)

        self.room_owner = User.objects.create_user(email="owner@test.com", password="pw")
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.room_owner,
            project_uuid=self.project_uuid,
        )

    def test_can_retrieve_as_room_owner(self):
        result = can_retrieve(self.room, self.room_owner, self.project_uuid)
        self.assertTrue(result)

    def test_can_retrieve_as_project_admin(self):
        admin = User.objects.create_user(email="admin@test.com", password="pw")
        ProjectPermission.objects.create(
            project=self.project,
            user=admin,
            role=ProjectPermission.ROLE_ADMIN,
        )

        result = can_retrieve(self.room, admin, self.project_uuid)
        self.assertTrue(result)

    def test_can_retrieve_as_sector_manager(self):
        manager = User.objects.create_user(email="manager@test.com", password="pw")
        permission = ProjectPermission.objects.create(
            project=self.project,
            user=manager,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=permission,
            sector=self.sector,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        result = can_retrieve(self.room, manager, self.project_uuid)
        self.assertTrue(result)

    def test_can_retrieve_denied_for_unrelated_user(self):
        outsider = User.objects.create_user(email="outsider@test.com", password="pw")
        result = can_retrieve(self.room, outsider, self.project_uuid)
        self.assertFalse(result)
