from datetime import timedelta

from django.test import TestCase

# from django.utils import timezone as django_timezone # Removed as it's no longer used

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.utils import calculate_response_time
from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue


class CalculateResponseTimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            rooms_limit=1,
            work_start="00:00:00",
            work_end="23:59:59",
            project=self.project,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(contact=self.contact, queue=self.queue)
        self.now = self.room.created_on

    def _create_message(self, sender, text, created_on_offset_seconds):
        return Message.objects.create(
            room=self.room,
            user=self.user if sender == "agent" else None,
            contact=self.contact if sender == "contact" else None,
            text=text,
            created_on=self.now + timedelta(seconds=created_on_offset_seconds),
        )

    def test_no_messages(self):
        self.assertEqual(calculate_response_time(self.room), 0)

    def test_only_agent_messages(self):
        self._create_message("agent", "Hello", 0)
        self._create_message("agent", "How are you?", 10)
        self.assertEqual(calculate_response_time(self.room), 0)

    def test_only_contact_messages(self):
        self._create_message("contact", "Hi", 0)
        self._create_message("contact", "I need help", 20)
        self.assertEqual(calculate_response_time(self.room), 0)

    def test_alternating_messages(self):
        # Message before the room was created (should be ignored)
        self._create_message("contact", "Hello", -100)

        # Contact sends a message
        self._create_message("contact", "Hello", 0)
        # Agent responds after 30 seconds
        self._create_message("agent", "Hi there!", 30)
        # Contact sends another message
        self._create_message("contact", "I have a question", 60)
        # Agent responds after 40 seconds
        self._create_message("agent", "Sure, what is it?", 100)

        # Expected average: (30 + 40) / 2 = 35
        self.assertEqual(calculate_response_time(self.room), 35)

    def test_multiple_contact_messages_before_agent_response(self):
        self._create_message("contact", "Hi", 0)
        self._create_message("contact", "Are you there?", 10)
        # Agent responds after 60 seconds from the *last* contact message
        self._create_message("agent", "Yes, I am here.", 10 + 60)

        # Expected average: 60 / 1 = 60
        self.assertEqual(calculate_response_time(self.room), 60)

    def test_multiple_agent_messages_after_contact_message(self):
        self._create_message("contact", "Hello", 0)
        # Agent responds after 20 seconds
        self._create_message("agent", "Hi!", 20)
        # Agent sends another message, this should not affect the response time calculation
        self._create_message("agent", "How can I help?", 30)

        # Expected average: 20 / 1 = 20
        self.assertEqual(calculate_response_time(self.room), 20)

    def test_contact_message_then_agent_then_contact_no_second_agent_response(self):
        self._create_message("contact", "Question 1", 0)
        self._create_message("agent", "Answer 1", 50)  # Response time = 50
        self._create_message("contact", "Question 2", 100)
        # No agent response to the second question

        # Expected average: 50 / 1 = 50
        self.assertEqual(calculate_response_time(self.room), 50)

    def test_no_agent_responses_at_all(self):
        self._create_message("contact", "Hello?", 0)
        self._create_message("contact", "Anyone there?", 10)
        self.assertEqual(calculate_response_time(self.room), 0)

    def test_messages_with_no_user_or_contact_are_ignored(self):
        # This scenario tests if messages without a user or contact (if possible by model constraints)
        # are correctly ignored by the filter Q(user__isnull=False) | Q(contact__isnull=False)
        # For this test, we will assume such messages might exist or be created by other means
        # and the function should gracefully ignore them.

        # Contact message
        Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Hello from contact",
            created_on=self.now + timedelta(seconds=0),
        )
        # Agent message
        Message.objects.create(
            room=self.room,
            user=self.user,
            text="Hello from agent",
            created_on=self.now + timedelta(seconds=30),  # Response time = 30
        )

        # A message with neither user nor contact
        Message.objects.create(
            room=self.room,
            text="",
            created_on=self.now + timedelta(seconds=15),  # Between contact and agent
        )

        # Contact message
        Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Another one from contact",
            created_on=self.now + timedelta(seconds=60),
        )
        # Agent message
        Message.objects.create(
            room=self.room,
            user=self.user,
            text="Another from agent",
            created_on=self.now + timedelta(seconds=100),  # Response time = 40
        )

        # Expected average: (30 + 40) / 2 = 35
        self.assertEqual(calculate_response_time(self.room), 35)

    def test_room_with_only_one_message_from_contact(self):
        self._create_message("contact", "Hello", 0)
        self.assertEqual(calculate_response_time(self.room), 0)

    def test_room_with_only_one_message_from_agent(self):
        self._create_message("agent", "Hello", 0)
        self.assertEqual(calculate_response_time(self.room), 0)

    def test_first_message_is_from_agent(self):
        self._create_message("agent", "Welcome!", 0)
        self._create_message("contact", "Hi", 10)
        self._create_message("agent", "How can I help?", 10 + 40)  # Response time = 40

        self.assertEqual(calculate_response_time(self.room), 20)
