from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.history.filters.rooms_filter import (
    filter_history_rooms_queryset_by_project_permission,
    get_history_rooms_queryset_by_contact,
    get_related_contact_ids,
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


class TestGetRelatedContactIds(TestCase):
    """
    Core logic that unifies Contacts by email or document, used by the
    history feature to concatenate conversations from different Contact
    rows (e.g. web chat users with rotating URNs).
    """

    def test_returns_only_self_when_no_email_and_no_document(self):
        contact = Contact.objects.create(name="John")
        related = list(get_related_contact_ids(contact))
        self.assertEqual(related, [contact.pk])

    def test_matches_contacts_with_same_email(self):
        target = Contact.objects.create(name="A", email="shared@x.com")
        other = Contact.objects.create(name="B", email="shared@x.com")
        Contact.objects.create(name="C", email="different@x.com")

        related = set(get_related_contact_ids(target))
        self.assertEqual(related, {target.pk, other.pk})

    def test_email_match_is_case_insensitive(self):
        target = Contact.objects.create(name="A", email="Shared@X.com")
        other = Contact.objects.create(name="B", email="shared@x.com")

        related = set(get_related_contact_ids(target))
        self.assertIn(other.pk, related)

    def test_matches_contacts_with_same_document(self):
        target = Contact.objects.create(name="A", document="12345678900")
        other = Contact.objects.create(name="B", document="12345678900")
        Contact.objects.create(name="C", document="99999999900")

        related = set(get_related_contact_ids(target))
        self.assertEqual(related, {target.pk, other.pk})

    def test_document_match_uses_normalized_value(self):
        """
        Contacts saved with different formattings share the same
        normalized document in DB, so they should be grouped together.
        """
        target = Contact.objects.create(name="A", document="123.456.789-00")
        other = Contact.objects.create(name="B", document="12345678900")

        related = set(get_related_contact_ids(target))
        self.assertIn(other.pk, related)

    def test_matches_by_email_or_document(self):
        target = Contact.objects.create(
            name="A", email="shared@x.com", document="111"
        )
        by_email = Contact.objects.create(name="B", email="shared@x.com")
        by_document = Contact.objects.create(name="C", document="111")
        Contact.objects.create(name="D", email="other@x.com", document="222")

        related = set(get_related_contact_ids(target))
        self.assertEqual(related, {target.pk, by_email.pk, by_document.pk})

    def test_ignores_empty_email(self):
        target = Contact.objects.create(name="A", email="")
        Contact.objects.create(name="B", email="")

        related = set(get_related_contact_ids(target))
        self.assertEqual(related, {target.pk})

    def test_ignores_empty_document(self):
        target = Contact.objects.create(name="A", document="")
        Contact.objects.create(name="B", document="")

        related = set(get_related_contact_ids(target))
        self.assertEqual(related, {target.pk})


class TestGetHistoryRoomsQuerysetByContact(TestCase):
    """
    Covers the full history-by-contact lookup that powers `has_history`
    and the history endpoint.
    """

    def setUp(self):
        self.user = User.objects.create(email="agent@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def _closed_room(self, contact):
        return Room.objects.create(
            contact=contact,
            queue=self.queue,
            is_active=False,
            ended_at=timezone.now(),
        )

    def test_includes_rooms_from_same_contact(self):
        contact = Contact.objects.create(name="Joao")
        room = self._closed_room(contact)

        qs = get_history_rooms_queryset_by_contact(
            contact, self.user, self.project
        )
        self.assertIn(room, qs)

    def test_includes_rooms_from_other_contacts_with_same_document(self):
        """
        Main scenario from the epic: web chat sessions use different URNs
        but the same CPF.
        """
        session_1 = Contact.objects.create(
            name="Joao", external_id="ws-1", document="123.456.789-00"
        )
        session_2 = Contact.objects.create(
            name="Joao", external_id="ws-2", document="12345678900"
        )
        room_1 = self._closed_room(session_1)
        room_2 = self._closed_room(session_2)

        qs = get_history_rooms_queryset_by_contact(
            session_2, self.user, self.project
        )
        self.assertIn(room_1, qs)
        self.assertIn(room_2, qs)

    def test_includes_rooms_from_other_contacts_with_same_email(self):
        session_1 = Contact.objects.create(
            name="Maria", external_id="ws-1", email="maria@x.com"
        )
        session_2 = Contact.objects.create(
            name="Maria", external_id="ws-2", email="maria@x.com"
        )
        room_1 = self._closed_room(session_1)

        qs = get_history_rooms_queryset_by_contact(
            session_2, self.user, self.project
        )
        self.assertIn(room_1, qs)

    def test_excludes_rooms_from_contacts_without_matching_email_or_document(self):
        target = Contact.objects.create(
            name="Joao", email="joao@x.com", document="111"
        )
        unrelated = Contact.objects.create(
            name="Other", email="other@x.com", document="222"
        )
        unrelated_room = self._closed_room(unrelated)

        qs = get_history_rooms_queryset_by_contact(
            target, self.user, self.project
        )
        self.assertNotIn(unrelated_room, qs)

    def test_excludes_active_rooms(self):
        contact = Contact.objects.create(name="Joao", document="111")
        active = Room.objects.create(
            contact=contact, queue=self.queue, is_active=True
        )

        qs = get_history_rooms_queryset_by_contact(
            contact, self.user, self.project
        )
        self.assertNotIn(active, qs)

    def test_returns_empty_when_user_has_no_permission_in_project(self):
        contact = Contact.objects.create(name="Joao")
        self._closed_room(contact)
        other_project = Project.objects.create(name="Other Project")

        qs = get_history_rooms_queryset_by_contact(
            contact, self.user, other_project
        )
        self.assertFalse(qs.exists())
