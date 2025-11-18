from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message, MessageMedia
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.sectors.models import Sector

User = get_user_model()


class BaseTestMessageViewSetV2(APITestCase):
    """Base class with helper methods for Message ViewSet V2 tests"""

    def list(self, params: dict = None) -> Response:
        url = reverse("message-v2-list")
        return self.client.get(url, params or {})


class TestMessageViewSetV2AsAnonymousUser(BaseTestMessageViewSetV2):
    """Tests for Messages ViewSet v2 as anonymous (unauthenticated) user"""

    def setUp(self):
        """Initial test setup"""
        # Create contact
        self.contact = Contact.objects.create(
            name="Maria Cliente", email="cliente@test.com"
        )

        # Create project
        self.project = Project.objects.create(name="Test Project")

        # Create sector
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        # Create queue
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        # Create active room
        self.room = Room.objects.create(
            contact=self.contact,
            is_active=True,
            queue=self.queue,
        )

    def test_list_messages_as_anonymous_user(self):
        """Tests that unauthenticated user cannot list messages"""
        response = self.list({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestMessageViewSetV2AsAuthenticatedUser(BaseTestMessageViewSetV2):
    """Tests for Messages ViewSet v2 as authenticated user"""

    def setUp(self):
        """Initial test setup"""
        # Create user/agent
        self.agent = User.objects.create_user(
            email="agent@test.com",
            password="testpass123",
            first_name="João",
            last_name="Silva",
        )

        # Create contact
        self.contact = Contact.objects.create(
            name="Maria Cliente", email="cliente@test.com"
        )

        # Create project
        self.project = Project.objects.create(name="Test Project")

        # Give agent permission on project
        self.project_permission = ProjectPermission.objects.create(
            user=self.agent, project=self.project, role=ProjectPermission.ROLE_ATTENDANT
        )

        # Create sector
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        # Create queue
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        # Create active room
        self.room = Room.objects.create(
            contact=self.contact,
            is_active=True,
            queue=self.queue,
            user=self.agent,  # Room assigned to agent
        )

        # Create test messages
        self.message_from_contact = Message.objects.create(
            room=self.room, contact=self.contact, text="Hello, I need help!", seen=False
        )

        self.message_from_agent = Message.objects.create(
            room=self.room, user=self.agent, text="Hello! How can I help?", seen=True
        )

        # Authenticate agent
        self.client.force_authenticate(user=self.agent)

    def test_list_messages_by_room(self):
        """Tests listing messages filtering by room - simulates agent fetching messages"""
        response = self.list({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

    def test_response_structure_contains_correct_v2_fields(self):
        """Tests if response structure contains correct v2 fields"""
        response = self.list({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get first message
        message_data = response.data["results"][0]

        # Check required fields
        expected_fields = [
            "uuid",
            "text",
            "user",
            "contact",
            "media",
            "replied_message",
            "seen",
            "is_delivered",
            "is_read",
            "internal_note",
            "is_automatic_message",
            "created_on",
        ]

        for field in expected_fields:
            self.assertIn(field, message_data, f"Field '{field}' missing in response")

        # Check fields that should NOT be present
        forbidden_fields = ["metadata", "status", "room", "external_id"]
        for field in forbidden_fields:
            self.assertNotIn(
                field, message_data, f"Field '{field}' should not be in response"
            )

    def test_user_field_has_correct_simplified_structure(self):
        """Tests if 'user' field has correct simplified structure"""
        response = self.list({"room": str(self.room.uuid)})

        # Find agent's message
        agent_message = None
        for msg in response.data["results"]:
            if msg["user"] is not None:
                agent_message = msg
                break

        self.assertIsNotNone(agent_message, "Agent message not found")

        # Check user structure - V2 simplified structure
        user_data = agent_message["user"]
        self.assertIn("first_name", user_data)
        self.assertIn("last_name", user_data)
        self.assertIn("email", user_data)
        self.assertEqual(user_data["first_name"], "João")
        self.assertEqual(user_data["last_name"], "Silva")
        self.assertEqual(user_data["email"], "agent@test.com")
        
        # Fields that should NOT be present (full User object fields)
        self.assertNotIn("photo_url", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("date_joined", user_data)

    def test_contact_field_has_correct_simplified_structure(self):
        """Tests if 'contact' field has correct simplified structure"""
        response = self.list({"room": str(self.room.uuid)})

        # Find contact's message
        contact_message = None
        for msg in response.data["results"]:
            if msg["contact"] is not None:
                contact_message = msg
                break

        self.assertIsNotNone(contact_message, "Contact message not found")

        # Check contact structure
        contact_data = contact_message["contact"]
        self.assertIn("uuid", contact_data)
        self.assertIn("name", contact_data)
        self.assertEqual(contact_data["name"], "Maria Cliente")

    def test_user_without_project_permission_cannot_access(self):
        """Tests that user without project permission cannot access"""
        # Create another user without project permission
        other_user = User.objects.create_user(
            email="other@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=other_user)

        # Since user has no project permission, should return error
        # v1 permission raises exception when ProjectPermission not found
        with self.assertRaises(Exception):
            self.list({"room": str(self.room.uuid)})

    def test_list_messages_with_media(self):
        """Tests listing messages with media array"""
        # Create message with media
        message_with_media = Message.objects.create(
            room=self.room, user=self.agent, text="Here is the document"
        )

        # Add media
        MessageMedia.objects.create(
            message=message_with_media,
            content_type="image/jpeg",
            media_url="https://example.com/image.jpg",
        )

        response = self.list({"room": str(self.room.uuid)})

        # Find message with media
        msg_with_media = None
        for msg in response.data["results"]:
            if msg["uuid"] == str(message_with_media.uuid):
                msg_with_media = msg
                break

        self.assertIsNotNone(msg_with_media)
        self.assertEqual(len(msg_with_media["media"]), 1)
        self.assertEqual(msg_with_media["media"][0]["content_type"], "image/jpeg")
        self.assertIn("url", msg_with_media["media"][0])
        self.assertIn("created_on", msg_with_media["media"][0])

    def test_message_with_replied_message(self):
        """Tests message with replied_message (without media - media only added when exists)"""
        # Create original message from contact
        original_message = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="What are your business hours?",
            external_id="ext-123",
        )

        # Create index for replied message
        ChatMessageReplyIndex.objects.create(
            external_id="ext-123", message=original_message
        )

        # Create reply message with metadata.context
        replied_message = Message.objects.create(
            room=self.room,
            user=self.agent,
            text="We operate from 9am to 6pm",
            metadata={"context": {"id": "ext-123"}},
        )

        response = self.list({"room": str(self.room.uuid)})

        # Find message with replied_message
        msg_with_reply = None
        for msg in response.data["results"]:
            if msg["uuid"] == str(replied_message.uuid):
                msg_with_reply = msg
                break

        self.assertIsNotNone(msg_with_reply)
        self.assertIsNotNone(msg_with_reply["replied_message"])
        
        # Check replied_message structure
        replied = msg_with_reply["replied_message"]
        self.assertEqual(replied["text"], "What are your business hours?")
        self.assertIn("uuid", replied)
        self.assertEqual(replied["uuid"], str(original_message.uuid))
        
        # Media should NOT be present when there's no media (V2 behavior fixed)
        self.assertNotIn("media", replied)
        
        # Contact should be present (original message is from contact)
        self.assertIn("contact", replied)
        self.assertEqual(replied["contact"]["uuid"], str(self.contact.uuid))
        self.assertEqual(replied["contact"]["name"], "Maria Cliente")

    def test_message_with_internal_note(self):
        """Tests message with internal note"""
        # Create message with internal note
        message = Message.objects.create(room=self.room, user=self.agent, text="")

        # Create internal note
        RoomNote.objects.create(
            room=self.room,
            user=self.agent,
            text="Customer seems interested",
            is_deletable=False,
            message=message,
        )

        response = self.list({"room": str(self.room.uuid)})

        # Find message with note
        msg_with_note = None
        for msg in response.data["results"]:
            if msg["uuid"] == str(message.uuid):
                msg_with_note = msg
                break

        self.assertIsNotNone(msg_with_note)
        self.assertIsNotNone(msg_with_note["internal_note"])
        self.assertEqual(
            msg_with_note["internal_note"]["text"], "Customer seems interested"
        )
        self.assertEqual(msg_with_note["internal_note"]["is_deletable"], False)

    def test_created_on_field_present_and_formatted(self):
        """Tests that created_on field is present and correctly formatted"""
        response = self.list({"room": str(self.room.uuid)})

        message_data = response.data["results"][0]
        self.assertIn("created_on", message_data)
        self.assertIsNotNone(message_data["created_on"])
        # Check that it's an ISO date string
        self.assertIsInstance(message_data["created_on"], str)

    def test_pagination_is_working(self):
        """Tests that pagination is working"""
        # Create more messages
        for i in range(25):
            Message.objects.create(room=self.room, user=self.agent, text=f"Message {i}")

        response = self.list({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_replied_message_with_media_includes_media_array(self):
        """Tests that replied_message includes media array when original message has media"""
        # Create original message with media
        original_message = Message.objects.create(
            room=self.room,
            user=self.agent,
            text="Here's the document",
            external_id="ext-media-123",
        )

        # Add media to original message
        MessageMedia.objects.create(
            message=original_message,
            content_type="application/pdf",
            media_url="https://example.com/document.pdf",
        )

        # Create index for replied message
        ChatMessageReplyIndex.objects.create(
            external_id="ext-media-123", message=original_message
        )

        # Create reply message
        replied_message = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Thanks for the document!",
            metadata={"context": {"id": "ext-media-123"}},
        )

        response = self.list({"room": str(self.room.uuid)})

        # Find message with replied_message
        msg_with_reply = None
        for msg in response.data["results"]:
            if msg["uuid"] == str(replied_message.uuid):
                msg_with_reply = msg
                break

        self.assertIsNotNone(msg_with_reply)
        replied = msg_with_reply["replied_message"]

        # Media SHOULD be present when original message has media
        self.assertIn("media", replied)
        self.assertEqual(len(replied["media"]), 1)
        self.assertEqual(replied["media"][0]["content_type"], "application/pdf")
        self.assertIn("url", replied["media"][0])

    def test_replied_message_with_user_has_correct_structure(self):
        """Tests that replied_message.user has correct structure (uuid + name)"""
        # Create original message from agent
        original_message = Message.objects.create(
            room=self.room,
            user=self.agent,
            text="What's your order number?",
            external_id="ext-user-123",
        )

        # Create index for replied message
        ChatMessageReplyIndex.objects.create(
            external_id="ext-user-123", message=original_message
        )

        # Create reply from contact
        replied_message = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="My order is #12345",
            metadata={"context": {"id": "ext-user-123"}},
        )

        response = self.list({"room": str(self.room.uuid)})

        # Find message with replied_message
        msg_with_reply = None
        for msg in response.data["results"]:
            if msg["uuid"] == str(replied_message.uuid):
                msg_with_reply = msg
                break

        self.assertIsNotNone(msg_with_reply)
        replied = msg_with_reply["replied_message"]

        # User should be present with correct structure (uuid + name)
        self.assertIn("user", replied)
        self.assertIn("uuid", replied["user"])
        self.assertIn("name", replied["user"])
        self.assertEqual(replied["user"]["uuid"], str(self.agent.pk))
        self.assertEqual(replied["user"]["name"], "João Silva")

    def test_message_with_invalid_replied_id_does_not_crash(self):
        """Tests that message with invalid replied_message ID doesn't cause error 500"""
        # Create message with metadata.context.id that doesn't exist in index
        message = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="This is a reply to non-existent message",
            metadata={"context": {"id": "non-existent-id-12345"}},
        )

        # Should NOT raise exception, should return 200 with replied_message as None
        response = self.list({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find our message
        msg = None
        for m in response.data["results"]:
            if m["uuid"] == str(message.uuid):
                msg = m
                break

        self.assertIsNotNone(msg)
        # replied_message should be None since the ID doesn't exist
        self.assertIsNone(msg["replied_message"])

    def test_message_with_empty_metadata_does_not_crash(self):
        """Tests that message with empty metadata doesn't cause errors"""
        # Create messages with different metadata states
        Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Message with empty metadata dict",
            metadata={},
        )

        Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Message with null metadata",
            metadata=None,
        )

        response = self.list({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return messages without errors
        self.assertGreaterEqual(len(response.data["results"]), 2)
