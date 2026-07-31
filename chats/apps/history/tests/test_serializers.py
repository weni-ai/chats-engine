from django.test import RequestFactory, TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.csat.models import CSATSurvey
from chats.apps.history.serializers.rooms import (
    RoomDetailSerializer,
    RoomHistorySerializer,
    _serialize_closed_by,
)
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestSerializeClosedBy(TestCase):
    """
    The contract requires `automatic_closed` to be carried *inside* the
    `closed_by` object. This payload must be coherent across three cases:
    manual closure (user only), automatic closure with user, and automatic
    closure with no user (typical for inactivity).
    """

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")
        self.user = User.objects.create(
            email="agent@example.com", first_name="Agent", last_name="Smith"
        )

    def _make_room(self, *, closed_by=None, automatic_closed=False) -> Room:
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.is_active = False
        room.ended_at = timezone.now()
        room.closed_by = closed_by
        room.automatic_closed = automatic_closed
        room.save()
        return room

    def test_returns_none_when_no_user_and_not_automatic(self):
        room = self._make_room()
        self.assertIsNone(_serialize_closed_by(room))

    def test_returns_user_with_automatic_false_for_manual_close(self):
        room = self._make_room(closed_by=self.user)
        payload = _serialize_closed_by(room)
        self.assertEqual(payload["first_name"], "Agent")
        self.assertEqual(payload["last_name"], "Smith")
        self.assertEqual(payload["email"], "agent@example.com")
        self.assertFalse(payload["automatic_closed"])

    def test_returns_user_with_automatic_true_when_both_set(self):
        room = self._make_room(closed_by=self.user, automatic_closed=True)
        payload = _serialize_closed_by(room)
        self.assertEqual(payload["email"], "agent@example.com")
        self.assertTrue(payload["automatic_closed"])

    def test_returns_payload_with_null_user_for_inactivity_close(self):
        room = self._make_room(closed_by=None, automatic_closed=True)
        payload = _serialize_closed_by(room)
        self.assertIsNone(payload["first_name"])
        self.assertIsNone(payload["last_name"])
        self.assertIsNone(payload["email"])
        self.assertTrue(payload["automatic_closed"])


class TestRoomHistorySerializerClosedBy(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")

    def test_history_serializer_includes_automatic_closed(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.is_active = False
        room.ended_at = timezone.now()
        room.automatic_closed = True
        room.save()

        data = RoomHistorySerializer(room).data
        self.assertIn("closed_by", data)
        self.assertTrue(data["closed_by"]["automatic_closed"])

    def test_detail_serializer_includes_automatic_closed(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.is_active = False
        room.ended_at = timezone.now()
        room.automatic_closed = True
        room.save()

        data = RoomDetailSerializer(room).data
        self.assertIn("closed_by", data)
        self.assertTrue(data["closed_by"]["automatic_closed"])

    def test_history_serializer_returns_none_for_old_open_close_flow(self):
        """
        Rooms closed by the legacy flow (no user, no automatic flag) must
        keep returning `closed_by: None` to preserve the existing behavior
        for the front.
        """
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.is_active = False
        room.ended_at = timezone.now()
        room.save()

        data = RoomHistorySerializer(room).data
        self.assertIsNone(data["closed_by"])


class TestRoomDetailSerializerCsat(TestCase):
    """
    CSAT rating/comment must only be visible to moderators (project admins),
    and must gracefully handle rooms without a completed CSAT survey.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")

        self.moderator = User.objects.create(email="moderator@example.com")
        ProjectPermission.objects.create(
            user=self.moderator, project=self.project, role=ProjectPermission.ROLE_ADMIN
        )

        self.attendant = User.objects.create(email="attendant@example.com")
        ProjectPermission.objects.create(
            user=self.attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    def _make_room(self) -> Room:
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.is_active = False
        room.ended_at = timezone.now()
        room.save()
        return room

    def _context_for(self, user) -> dict:
        request = self.factory.get("/")
        request.user = user
        return {"request": request}

    def test_moderator_sees_rating_and_comment(self):
        room = self._make_room()
        CSATSurvey.objects.create(
            room=room,
            rating=5,
            comment="Great service",
            answered_on=timezone.now(),
        )

        data = RoomDetailSerializer(
            room, context=self._context_for(self.moderator)
        ).data

        self.assertEqual(data["csat_note"], 5)
        self.assertEqual(data["csat_commentary"], "Great service")

    def test_non_moderator_does_not_see_rating_or_comment(self):
        room = self._make_room()
        CSATSurvey.objects.create(
            room=room,
            rating=5,
            comment="Great service",
            answered_on=timezone.now(),
        )

        data = RoomDetailSerializer(
            room, context=self._context_for(self.attendant)
        ).data

        self.assertIsNone(data["csat_note"])
        self.assertIsNone(data["csat_commentary"])

    def test_moderator_sees_none_when_no_csat_answered(self):
        room = self._make_room()

        data = RoomDetailSerializer(
            room, context=self._context_for(self.moderator)
        ).data

        self.assertIsNone(data["csat_note"])
        self.assertIsNone(data["csat_commentary"])

    def test_moderator_sees_rating_without_comment(self):
        room = self._make_room()
        CSATSurvey.objects.create(
            room=room,
            rating=4,
            comment=None,
            answered_on=timezone.now(),
        )

        data = RoomDetailSerializer(
            room, context=self._context_for(self.moderator)
        ).data

        self.assertEqual(data["csat_note"], 4)
        self.assertIsNone(data["csat_commentary"])

    def test_no_request_in_context_hides_csat_fields(self):
        """
        Defensive behavior: without a request in context we can't determine
        the requester's role, so CSAT data must not leak.
        """
        room = self._make_room()
        CSATSurvey.objects.create(
            room=room,
            rating=5,
            comment="Great service",
            answered_on=timezone.now(),
        )

        data = RoomDetailSerializer(room).data

        self.assertIsNone(data["csat_note"])
        self.assertIsNone(data["csat_commentary"])
