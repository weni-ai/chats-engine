from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message, MessageMedia
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.sectors.models import Sector

User = get_user_model()


class MessageViewSetV2Tests(APITestCase):
    """
    Tests for Messages ViewSet v2
    Simulates an agent fetching messages from a room
    """

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
        """
        Tests listing messages filtering by room
        Simulates agent fetching messages from room
        """
        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)
        """
        Tests if response structure contains correct v2 fields
        """
        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

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
        """
        Tests if 'user' field has correct simplified structure
        """
        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

        # Find agent's message
        agent_message = None
        for msg in response.data["results"]:
            if msg["user"] is not None:
                agent_message = msg
                break

        self.assertIsNotNone(agent_message, "Agent message not found")

        # Check user structure
        user_data = agent_message["user"]
        self.assertIn("first_name", user_data)
        self.assertIn("last_name", user_data)
        self.assertIn("email", user_data)
        self.assertEqual(user_data["first_name"], "João")
        self.assertEqual(user_data["last_name"], "Silva")
        self.assertEqual(user_data["email"], "agent@test.com")
        """
        Tests if 'contact' field has correct simplified structure
        """
        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

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
        """
        Tests that unauthenticated user cannot list messages
        """
        self.client.force_authenticate(user=None)
        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        """
        Tests that user without project permission cannot access
        """
        # Create another user without project permission
        other_user = User.objects.create_user(
            email="other@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=other_user)

        url = reverse("message-v2-list")

        # Since user has no project permission, should return error
        # v1 permission raises exception when ProjectPermission not found
        with self.assertRaises(Exception):
            self.client.get(url, {"room": str(self.room.uuid)})
        """
        Tests listing messages with media array
        """
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

        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

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
        """
        Tests message with replied_message (with media array)
        """
        # Create original message
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

        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

        # Find message with replied_message
        msg_with_reply = None
        for msg in response.data["results"]:
            if msg["uuid"] == str(replied_message.uuid):
                msg_with_reply = msg
                break

        self.assertIsNotNone(msg_with_reply)
        self.assertIsNotNone(msg_with_reply["replied_message"])
        self.assertEqual(
            msg_with_reply["replied_message"]["text"], "What are your business hours?"
        )
        self.assertIn("media", msg_with_reply["replied_message"])
        """
        Tests message with internal note
        """
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

        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

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
        """
        Tests that created_on field is present and correctly formatted
        """
        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

        message_data = response.data["results"][0]
        self.assertIn("created_on", message_data)
        self.assertIsNotNone(message_data["created_on"])
        # Check that it's an ISO date string
        self.assertIsInstance(message_data["created_on"], str)
        """
        Tests that pagination is working
        """
        # Create more messages
        for i in range(25):
            Message.objects.create(room=self.room, user=self.agent, text=f"Message {i}")

        url = reverse("message-v2-list")
        response = self.client.get(url, {"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
