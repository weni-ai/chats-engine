from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.history.filters.rooms_filter import (
    filter_history_rooms_queryset_by_project_permission,
)
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue, QueueAuthorization


class TestHistoryRoomFilter(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def _create_user_permission(self, role: int):
        return ProjectPermission.objects.create(
            user=self.user, project=self.project, role=role
        )

    def test_filter_history_rooms_queryset_by_project_permission_when_room_is_active(
        self,
    ):
        user_permission = self._create_user_permission(ProjectPermission.ROLE_ADMIN)
        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=True,
        )

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertNotIn(room, queryset)

    def test_filter_history_rooms_queryset_by_project_permission_when_contact_is_blocked(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ADMIN
        )

        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=True,
        )

        self.project.config = {"history_contacts_blocklist": [room.contact.external_id]}
        self.project.save(update_fields=["config"])

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertNotIn(room, queryset)

    def test_filter_history_rooms_queryset_by_project_permission_when_user_is_admin(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ADMIN
        )
        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
        )

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertIn(room, queryset)

    def test_filter_history_rooms_qs_by_perm_when_user_is_agent_and_can_see_queue_history_and_user_is_in_queue(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ATTENDANT
        )
        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
        )

        QueueAuthorization.objects.create(
            permission=user_permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.project.config = {"agents_can_see_queue_history": True}
        self.project.save(update_fields=["config"])

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertIn(room, queryset)

    def test_filter_history_rooms_qs_by_perm_when_user_is_agent_and_can_see_queue_history_and_user_is_not_in_queue(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ATTENDANT
        )

        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
        )

        self.project.config = {"agents_can_see_queue_history": True}
        self.project.save(update_fields=["config"])

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertNotIn(room, queryset)

    def test_filter_history_rooms_qs_by_perm_when_user_is_agent_and_can_see_queue_history_and_user_is_assigned_to_room(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ATTENDANT
        )

        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
            user=self.user,
        )

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertIn(room, queryset)

    def test_filter_history_rooms_qs_by_perm_when_user_is_agent_and_cannot_see_queue_history_and_is_not_assigned(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ATTENDANT
        )

        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
        )

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertNotIn(room, queryset)

    def test_filter_history_rooms_qs_by_perm_when_user_is_agent_and_cannot_see_queue_history_and_is_assigned(
        self,
    ):
        user_permission = self._create_user_permission(
            role=ProjectPermission.ROLE_ATTENDANT
        )

        room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact"),
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
            user=self.user,
        )

        queryset = filter_history_rooms_queryset_by_project_permission(
            Room.objects.all(), user_permission=user_permission
        )

        self.assertIn(room, queryset)
