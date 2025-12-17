from django.test import TestCase

from chats.apps.api.v1.rooms.serializers import BulkTransferSerializer
from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class BulkTransferSerializerTest(TestCase):
    def setUp(self):
        # Create users
        self.request_user = User.objects.create(email="request@test.com")
        self.target_user = User.objects.create(email="target@test.com")
        self.other_user = User.objects.create(email="other@test.com")

        # Create projects
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.other_project = Project.objects.create(
            name="Other Project", timezone="UTC"
        )

        # Create project permissions
        ProjectPermission.objects.create(
            project=self.project,
            user=self.request_user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.target_user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.target_user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        # Create sectors
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        # Create queues
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.other_queue = Queue.objects.create(name="Other Queue", sector=self.sector)
        self.other_project_queue = Queue.objects.create(
            name="Other Project Queue", sector=self.other_sector
        )

        # Create contacts
        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )
        self.contact2 = Contact.objects.create(
            name="Test Contact 2", email="contact2@test.com"
        )
        self.contact3 = Contact.objects.create(
            name="Test Contact 3", email="contact3@test.com"
        )

        # Create rooms
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.room2 = Room.objects.create(queue=self.queue, contact=self.contact2)
        self.other_project_room = Room.objects.create(
            queue=self.other_project_queue, contact=self.contact3
        )

    def _get_serializer_context(self, user=None):
        """Helper to create serializer context with request and user"""

        class MockRequest:
            def __init__(self, user):
                self.user = user

        request = MockRequest(user or self.request_user)
        return {"request": request}

    def test_valid_serializer_with_user_email(self):
        """Test serializer is valid with user_email"""
        data = {
            "user_email": self.target_user.email,
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["user"], self.target_user)
        self.assertIsNone(serializer.validated_data["queue"])
        self.assertEqual(list(serializer.validated_data["rooms"]), [self.room])

    def test_valid_serializer_with_queue_uuid(self):
        """Test serializer is valid with queue_uuid"""
        data = {
            "queue_uuid": str(self.other_queue.uuid),
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["queue"], self.other_queue)
        self.assertIsNone(serializer.validated_data["user"])
        self.assertEqual(list(serializer.validated_data["rooms"]), [self.room])

    def test_valid_serializer_with_both_user_email_and_queue_uuid(self):
        """Test serializer is valid with both user_email and queue_uuid"""
        data = {
            "user_email": self.target_user.email,
            "queue_uuid": str(self.other_queue.uuid),
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["user"], self.target_user)
        self.assertEqual(serializer.validated_data["queue"], self.other_queue)
        self.assertEqual(list(serializer.validated_data["rooms"]), [self.room])

    def test_invalid_serializer_missing_both_user_email_and_queue_uuid(self):
        """Test serializer is invalid when both user_email and queue_uuid are missing"""
        data = {
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("user_email", serializer.errors)
        self.assertIn(
            "user_email or queue_uuid is required", str(serializer.errors["user_email"])
        )

    def test_valid_serializer_empty_rooms_list(self):
        """Test serializer is valid with empty rooms_list (no rooms to transfer)"""
        data = {
            "user_email": self.target_user.email,
            "rooms_list": [],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(len(serializer.validated_data["rooms"]), 0)

    def test_invalid_serializer_missing_rooms_list(self):
        """Test serializer is invalid when rooms_list is missing"""
        data = {
            "user_email": self.target_user.email,
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("rooms_list", serializer.errors)

    def test_invalid_queue_uuid_not_found(self):
        """Test serializer is invalid when queue_uuid doesn't exist"""
        from uuid import uuid4

        data = {
            "queue_uuid": str(uuid4()),
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("queue_uuid", serializer.errors)
        self.assertIn("Queue not found", str(serializer.errors["queue_uuid"]))

    def test_invalid_queue_uuid_user_no_permission(self):
        """Test serializer is invalid when user has no permission on queue's project"""
        # Create user without permission
        no_permission_user = User.objects.create(email="noperm@test.com")

        data = {
            "queue_uuid": str(self.queue.uuid),
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context(user=no_permission_user)
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("queue_uuid", serializer.errors)
        self.assertIn(
            "User has no permission on the project",
            str(serializer.errors["queue_uuid"]),
        )

    def test_invalid_transfer_rooms_from_different_project_to_queue(self):
        """Test serializer is invalid when transferring rooms from different project to queue"""
        data = {
            "queue_uuid": str(self.queue.uuid),
            "rooms_list": [str(self.other_project_room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("error", serializer.errors)
        self.assertIn(
            "Cannot transfer rooms from a project to another",
            str(serializer.errors["error"]),
        )

    def test_invalid_user_email_no_permission_on_room_project(self):
        """Test serializer is invalid when user has no permission on room's project"""
        # Create user without permission on other_project
        no_permission_user = User.objects.create(email="noperm@test.com")
        ProjectPermission.objects.create(
            project=self.project,
            user=no_permission_user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        # But not on other_project

        data = {
            "user_email": no_permission_user.email,
            "rooms_list": [str(self.other_project_room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("error", serializer.errors)
        self.assertIn(
            "User has no permission on the project", str(serializer.errors["error"])
        )

    def test_valid_multiple_rooms_same_project(self):
        """Test serializer is valid with multiple rooms from same project"""
        data = {
            "user_email": self.target_user.email,
            "rooms_list": [str(self.room.uuid), str(self.room2.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(len(serializer.validated_data["rooms"]), 2)
        self.assertIn(self.room, serializer.validated_data["rooms"])
        self.assertIn(self.room2, serializer.validated_data["rooms"])

    def test_invalid_multiple_rooms_different_projects(self):
        """Test serializer is invalid with multiple rooms from different projects"""
        data = {
            "user_email": self.target_user.email,
            "rooms_list": [str(self.room.uuid), str(self.other_project_room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        # This should fail because target_user might not have permission on both projects
        # Actually, target_user has permission on both, so let's test with a user that doesn't
        limited_user = User.objects.create(email="limited@test.com")
        ProjectPermission.objects.create(
            project=self.project, user=limited_user, role=ProjectPermission.ROLE_ADMIN
        )
        # limited_user doesn't have permission on other_project

        data = {
            "user_email": limited_user.email,
            "rooms_list": [str(self.room.uuid), str(self.other_project_room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("error", serializer.errors)
        self.assertIn(
            "User has no permission on the project", str(serializer.errors["error"])
        )

    def test_invalid_room_uuid_not_found(self):
        """Test serializer handles non-existent room UUIDs gracefully"""
        from uuid import uuid4

        data = {
            "user_email": self.target_user.email,
            "rooms_list": [str(uuid4())],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        # The serializer should be valid but rooms queryset will be empty
        self.assertTrue(serializer.is_valid())
        self.assertEqual(len(serializer.validated_data["rooms"]), 0)

    def test_invalid_user_email_not_found(self):
        """Test serializer is invalid when user email doesn't exist (no permissions)"""
        data = {
            "user_email": "nonexistent@test.com",
            "rooms_list": [str(self.room.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        # The serializer should be invalid because user has no permissions
        self.assertFalse(serializer.is_valid())
        self.assertIn("error", serializer.errors)
        self.assertIn(
            "User has no permission on the project", str(serializer.errors["error"])
        )

    def test_valid_transfer_to_queue_same_project(self):
        """Test valid transfer to queue in same project"""
        data = {
            "queue_uuid": str(self.other_queue.uuid),
            "rooms_list": [str(self.room.uuid), str(self.room2.uuid)],
        }
        serializer = BulkTransferSerializer(
            data=data, context=self._get_serializer_context()
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["queue"], self.other_queue)
        self.assertEqual(len(serializer.validated_data["rooms"]), 2)
