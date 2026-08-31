from datetime import time

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.exceptions import MessageCreateError
from chats.apps.msgs.validators.agent_message_create import (
    validate_agent_can_create_message,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestValidateAgentCanCreateMessage(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="agent@example.com",
            password="testpass123",
            first_name="Agent",
            last_name="User",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            name="Contact", email="contact@example.com"
        )
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        self.project_permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
            last_seen=timezone.now(),
        )

    def test_allows_assigned_agent(self):
        validate_agent_can_create_message(self.user, self.room)

    def test_denies_other_agent(self):
        self.room.user = self.other_user
        self.room.save(update_fields=["user"])

        with self.assertRaises(MessageCreateError) as ctx:
            validate_agent_can_create_message(self.user, self.room)

        self.assertEqual(ctx.exception.error_code, "permission_denied")

    def test_denies_offline_agent_when_config_enabled(self):
        self.project.config = {"restrict_offline_agents": True}
        self.project.save(update_fields=["config"])
        self.project_permission.status = ProjectPermission.STATUS_OFFLINE
        self.project_permission.save(update_fields=["status"])

        with self.assertRaises(MessageCreateError) as ctx:
            validate_agent_can_create_message(self.user, self.room)

        self.assertEqual(ctx.exception.error_code, "agent_offline")
