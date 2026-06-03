"""
Tests for the `weniChatsInactivityTimeout` feature flag gating applied to
the inactivity usecase, the `Room.notify_inactivity` notification and the
room serializers.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.rooms.serializers import ListRoomSerializer
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.usecases.inactivity import InactivityService
from chats.apps.sectors.models import Sector


_INACTIVITY_CONFIG = {
    "is_message_timeout_enabled": True,
    "message_timeout_text": "Are you still there?",
    "message_timeout_time": 600,
    "is_close_room_enabled": True,
    "close_room_message_text": "Closing due to inactivity.",
    "close_room_timeout_time": 60,
}


class InactivityFeatureFlagUsecaseTests(TestCase):
    """
    With the feature flag turned off the usecase must skip warning, closure
    and reset operations even when the room/sector data is otherwise eligible.
    """

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            inactivity_timeout=_INACTIVITY_CONFIG,
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")

    def _create_eligible_room(self, *, already_warned: bool = False) -> Room:
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.last_message_user = self.user
        room.last_interaction = timezone.now() - timedelta(seconds=700)
        room.is_inactive = already_warned
        room.save()
        return room

    @patch(
        "chats.apps.rooms.usecases.inactivity.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_warn_skipped_when_feature_flag_off(self, _mock_ff):
        room = self._create_eligible_room()

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)

    @patch(
        "chats.apps.rooms.usecases.inactivity.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_close_skipped_when_feature_flag_off(self, _mock_ff):
        room = self._create_eligible_room(already_warned=True)

        with patch.object(Room, "notify_user"):
            closed = InactivityService().close_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(closed, 0)
        self.assertTrue(room.is_active)

    @patch(
        "chats.apps.rooms.usecases.inactivity.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_reset_skipped_when_feature_flag_off(self, _mock_ff):
        room = self._create_eligible_room(already_warned=True)

        with patch.object(Room, "notify_inactivity") as mock_notify:
            cleared = InactivityService().reset_inactivity(room)

        self.assertFalse(cleared)
        mock_notify.assert_not_called()

    @patch(
        "chats.apps.rooms.usecases.inactivity.is_feature_active_for_attributes",
        return_value=True,
    )
    def test_feature_flag_evaluation_is_cached_per_service_instance(self, mock_ff):
        # Two eligible rooms in the same project must trigger only ONE
        # feature flag evaluation thanks to the per-instance cache.
        for i in range(2):
            contact = Contact.objects.create(name=f"contact-{i}", external_id=f"c-{i}")
            room = Room.objects.create(queue=self.queue, contact=contact)
            room.user = self.user
            room.last_message_user = self.user
            room.last_interaction = timezone.now() - timedelta(seconds=700)
            room.save()

        with patch.object(Room, "notify_inactivity"):
            InactivityService().warn_inactive_rooms()

        self.assertEqual(mock_ff.call_count, 1)


class NotifyInactivityFeatureFlagTests(TestCase):
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
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.room.user = self.user
        self.room.save()

    @patch(
        "chats.apps.rooms.usecases.inactivity.is_feature_active_for_attributes",
        return_value=False,
    )
    @patch("chats.apps.rooms.models.send_channels_group")
    def test_notify_inactivity_does_not_emit_when_feature_flag_off(
        self, mock_send, _mock_ff
    ):
        permission_mock = MagicMock(pk=42)
        with patch.object(Room, "get_permission", return_value=permission_mock):
            self.room.is_inactive = True
            self.room.notify_inactivity()

        mock_send.assert_not_called()


class SerializerFeatureFlagTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            inactivity_timeout=_INACTIVITY_CONFIG,
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.room.is_inactive = True
        self.room.save()

    @patch(
        "chats.apps.api.v1.rooms.serializers.is_inactivity_feature_active",
        return_value=False,
    )
    def test_list_serializer_hides_is_inactive_when_feature_flag_off(self, _mock_ff):
        data = ListRoomSerializer(self.room).data

        self.assertFalse(data["is_inactive"])
        self.assertEqual(data["inactivity_timeout_time"], 0)

    @patch(
        "chats.apps.api.v1.rooms.serializers.is_inactivity_feature_active",
        return_value=True,
    )
    def test_list_serializer_exposes_is_inactive_when_feature_flag_on(self, _mock_ff):
        data = ListRoomSerializer(self.room).data

        self.assertTrue(data["is_inactive"])
        self.assertEqual(data["inactivity_timeout_time"], 600)
