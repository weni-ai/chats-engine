from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from chats.apps.api.v1.rooms.permissions import (
    CanAddOrRemoveRoomTagPermission,
    RoomNoteMediaPermission,
    RoomNotePermission,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.sectors.models import Sector


User = get_user_model()


class CanAddOrRemoveRoomTagPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="tag@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.perm = CanAddOrRemoveRoomTagPermission()

    def test_no_room_user(self):
        obj = SimpleNamespace(user=None)
        request = SimpleNamespace(user=self.user)
        self.assertFalse(self.perm.has_object_permission(request, None, obj))

    def test_room_owner(self):
        obj = SimpleNamespace(user=self.user)
        request = SimpleNamespace(user=self.user)
        self.assertTrue(self.perm.has_object_permission(request, None, obj))

    def test_not_owner(self):
        obj = SimpleNamespace(user=self.other)
        request = SimpleNamespace(user=self.user)
        self.assertFalse(self.perm.has_object_permission(request, None, obj))


class RoomNotePermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="note@example.com", password="x")
        self.other = User.objects.create_user(email="note2@example.com", password="x")
        self.project = Project.objects.create(name="P")
        self.sector = Sector.objects.create(
            name="S",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Q", sector=self.sector)
        self.contact = Contact.objects.create(name="C")
        self.room = Room.objects.create(
            queue=self.queue, user=self.user, contact=self.contact
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.other,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.perm = RoomNotePermission()

    def _request(self, user, data=None, query_params=None):
        return SimpleNamespace(
            user=user,
            data=data or {},
            query_params=query_params or {},
        )

    def test_other_action_delegates(self):
        view = SimpleNamespace(action="retrieve")
        request = self._request(self.user)
        self.assertTrue(self.perm.has_permission(request, view))

    def test_list_as_room_owner(self):
        view = SimpleNamespace(action="list")
        request = self._request(
            self.user, query_params={"room": str(self.room.uuid)}
        )
        self.assertTrue(self.perm.has_permission(request, view))

    def test_list_as_project_admin(self):
        view = SimpleNamespace(action="list")
        request = self._request(
            self.other, query_params={"room": str(self.room.uuid)}
        )
        self.assertTrue(self.perm.has_permission(request, view))

    def test_create_denied_for_non_owner(self):
        view = SimpleNamespace(action="create")
        request = self._request(
            self.other, data={"room": str(self.room.uuid)}
        )
        self.assertFalse(self.perm.has_permission(request, view))

    def test_list_via_project_param(self):
        view = SimpleNamespace(action="list")
        request = self._request(
            self.other, query_params={"project": str(self.project.uuid)}
        )
        self.assertTrue(self.perm.has_permission(request, view))

    def test_list_no_room_no_project(self):
        view = SimpleNamespace(action="list")
        request = self._request(self.other, query_params={})
        self.assertFalse(self.perm.has_permission(request, view))

    def test_list_unknown_project(self):
        import uuid

        view = SimpleNamespace(action="list")
        request = self._request(
            self.other, query_params={"project": str(uuid.uuid4())}
        )
        self.assertFalse(self.perm.has_permission(request, view))

    def test_list_room_without_permission(self):
        stranger = User.objects.create_user(email="stranger@example.com", password="x")
        view = SimpleNamespace(action="list")
        request = self._request(
            stranger, query_params={"room": str(self.room.uuid)}
        )
        self.assertFalse(self.perm.has_permission(request, view))


class RoomNoteMediaPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="media@example.com", password="x")
        self.admin = User.objects.create_user(email="mediaadmin@example.com", password="x")
        self.project = Project.objects.create(name="P")
        self.sector = Sector.objects.create(
            name="S",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Q", sector=self.sector)
        self.contact = Contact.objects.create(name="C")
        self.room = Room.objects.create(
            queue=self.queue, user=self.user, contact=self.contact
        )
        self.note = RoomNote.objects.create(room=self.room, user=self.user, text="n")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.perm = RoomNoteMediaPermission()

    def test_create_as_room_owner(self):
        view = SimpleNamespace(action="create")
        request = SimpleNamespace(user=self.user, data={"note": str(self.note.uuid)})
        self.assertTrue(self.perm.has_permission(request, view))

    def test_create_denied(self):
        view = SimpleNamespace(action="create")
        request = SimpleNamespace(user=self.admin, data={"note": str(self.note.uuid)})
        self.assertFalse(self.perm.has_permission(request, view))

    def test_create_missing_note(self):
        import uuid

        view = SimpleNamespace(action="create")
        request = SimpleNamespace(user=self.user, data={"note": str(uuid.uuid4())})
        self.assertFalse(self.perm.has_permission(request, view))

    def test_list_requires_room_or_project(self):
        view = SimpleNamespace(action="list")
        request = SimpleNamespace(user=self.user, query_params={})
        with self.assertRaises(ValidationError):
            self.perm.has_permission(request, view)

    def test_list_as_room_owner(self):
        view = SimpleNamespace(action="list")
        request = SimpleNamespace(
            user=self.user, query_params={"room": str(self.room.uuid)}
        )
        self.assertTrue(self.perm.has_permission(request, view))

    def test_list_as_project_admin_via_room(self):
        view = SimpleNamespace(action="list")
        request = SimpleNamespace(
            user=self.admin, query_params={"room": str(self.room.uuid)}
        )
        self.assertTrue(self.perm.has_permission(request, view))

    def test_list_via_project_only(self):
        view = SimpleNamespace(action="list")
        request = SimpleNamespace(
            user=self.admin, query_params={"project": str(self.project.uuid)}
        )
        self.assertTrue(self.perm.has_permission(request, view))

    def test_list_unknown_room_without_project(self):
        import uuid

        view = SimpleNamespace(action="list")
        request = SimpleNamespace(
            user=self.admin, query_params={"room": str(uuid.uuid4())}
        )
        self.assertFalse(self.perm.has_permission(request, view))

    def test_other_action_delegates(self):
        view = SimpleNamespace(action="retrieve")
        request = SimpleNamespace(user=self.user, query_params={})
        self.assertTrue(self.perm.has_permission(request, view))

    def test_has_object_permission(self):
        media = SimpleNamespace(note=self.note)
        request = SimpleNamespace(user=self.user)
        self.assertTrue(self.perm.has_object_permission(request, None, media))

    def test_has_object_permission_denied(self):
        media = SimpleNamespace(note=self.note)
        request = SimpleNamespace(user=self.admin)
        self.assertFalse(self.perm.has_object_permission(request, None, media))
