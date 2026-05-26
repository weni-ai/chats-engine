from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.usecases.inactivity import (
    INACTIVITY_END_BY,
    InactivityService,
    _send_silent_automatic_message,
)
from chats.apps.sectors.models import Sector


def _enabled_inactivity_config(
    *, message_timeout_time=600, close_room_timeout_time=60, close_enabled=True
):
    return {
        "is_message_timeout_enabled": True,
        "message_timeout_text": "Are you still there?",
        "message_timeout_time": message_timeout_time,
        "is_close_room_enabled": close_enabled,
        "close_room_message_text": "Closing due to inactivity.",
        "close_room_timeout_time": close_room_timeout_time,
    }


class InactivityWarnTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            inactivity_timeout=_enabled_inactivity_config(),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")

    def _create_eligible_room(self, last_interaction_offset_seconds: int = 700) -> Room:
        last_interaction = timezone.now() - timedelta(
            seconds=last_interaction_offset_seconds
        )

        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.last_message_user = self.user
        room.last_interaction = last_interaction
        room.save()

        return room

    def test_eligible_room_is_warned(self):
        room = self._create_eligible_room()

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 1)
        self.assertTrue(room.is_inactive)
        self.assertTrue(
            Message.objects.filter(
                room=room, text="Are you still there?", user=self.user
            ).exists()
        )

    def test_room_within_timeout_is_not_warned(self):
        room = self._create_eligible_room(last_interaction_offset_seconds=60)

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)

    def test_room_without_assigned_user_is_skipped(self):
        room = self._create_eligible_room()
        Room.objects.filter(pk=room.pk).update(user=None)

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)

    def test_room_where_contact_replied_last_is_skipped(self):
        room = self._create_eligible_room()
        Room.objects.filter(pk=room.pk).update(
            last_message_user=None, last_message_contact=self.contact
        )

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)

    def test_waiting_room_is_skipped(self):
        room = self._create_eligible_room()
        Room.objects.filter(pk=room.pk).update(is_waiting=True)

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)

    def test_sector_with_alert_disabled_does_not_warn(self):
        room = self._create_eligible_room()
        self.sector.inactivity_timeout = _enabled_inactivity_config()
        self.sector.inactivity_timeout["is_message_timeout_enabled"] = False
        self.sector.save()

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)

    def test_sector_without_inactivity_config_does_not_warn(self):
        room = self._create_eligible_room()
        self.sector.inactivity_timeout = None
        self.sector.save()

        with patch.object(Room, "notify_inactivity"):
            warned = InactivityService().warn_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(warned, 0)
        self.assertFalse(room.is_inactive)


class InactivityCloseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            inactivity_timeout=_enabled_inactivity_config(),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")

    def _create_already_warned_room(
        self, last_interaction_offset_seconds: int = 700
    ) -> Room:
        last_interaction = timezone.now() - timedelta(
            seconds=last_interaction_offset_seconds
        )

        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.last_message_user = self.user
        room.last_interaction = last_interaction
        room.is_inactive = True
        room.save()

        return room

    def test_warned_room_past_close_timeout_is_closed(self):
        # 600 (warn) + 60 (close) = 660s required; offset 700s exceeds it.
        room = self._create_already_warned_room(last_interaction_offset_seconds=700)

        with patch.object(Room, "notify_user"):
            closed = InactivityService().close_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(closed, 1)
        self.assertFalse(room.is_active)
        self.assertEqual(room.ended_by, INACTIVITY_END_BY)
        self.assertTrue(
            Message.objects.filter(
                room=room, text="Closing due to inactivity.", user=self.user
            ).exists()
        )

    def test_warned_room_within_close_timeout_is_not_closed(self):
        # 600 (warn) + 60 (close) = 660s required; offset 620s is within.
        room = self._create_already_warned_room(last_interaction_offset_seconds=620)

        with patch.object(Room, "notify_user"):
            closed = InactivityService().close_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(closed, 0)
        self.assertTrue(room.is_active)

    def test_room_with_close_disabled_is_not_closed(self):
        room = self._create_already_warned_room(last_interaction_offset_seconds=700)
        self.sector.inactivity_timeout = _enabled_inactivity_config(close_enabled=False)
        self.sector.save()

        with patch.object(Room, "notify_user"):
            closed = InactivityService().close_inactive_rooms()

        room.refresh_from_db()
        self.assertEqual(closed, 0)
        self.assertTrue(room.is_active)

    def test_active_non_warned_room_is_not_closed(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.last_message_user = self.user
        room.last_interaction = timezone.now() - timedelta(seconds=700)
        room.save()
        self.assertFalse(room.is_inactive)

        with patch.object(Room, "notify_user"):
            closed = InactivityService().close_inactive_rooms()

        room.refresh_from_db()
        self.assertTrue(room.is_active)


class InactivityResetTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
            inactivity_timeout=_enabled_inactivity_config(),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")

    def _create_inactive_room(self) -> Room:
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.last_message_user = self.user
        room.last_interaction = timezone.now()
        room.is_inactive = True
        room.save()
        return room

    def test_reset_clears_flag_when_room_is_inactive(self):
        room = self._create_inactive_room()

        with patch.object(Room, "notify_inactivity") as mock_notify:
            cleared = InactivityService().reset_inactivity(room)

        room.refresh_from_db()
        self.assertTrue(cleared)
        self.assertFalse(room.is_inactive)
        mock_notify.assert_called_once_with()

    def test_reset_is_no_op_when_room_already_active(self):
        room = self._create_inactive_room()
        Room.objects.filter(pk=room.pk).update(is_inactive=False)
        room.refresh_from_db()

        with patch.object(Room, "notify_inactivity") as mock_notify:
            cleared = InactivityService().reset_inactivity(room)

        self.assertFalse(cleared)
        mock_notify.assert_not_called()

    def test_reset_is_no_op_when_room_is_closed(self):
        room = self._create_inactive_room()
        Room.objects.filter(pk=room.pk).update(is_active=False)
        room.refresh_from_db()

        with patch.object(Room, "notify_inactivity") as mock_notify:
            cleared = InactivityService().reset_inactivity(room)

        self.assertFalse(cleared)
        mock_notify.assert_not_called()

    def test_on_new_message_from_contact_resets_inactive_room(self):
        room = self._create_inactive_room()
        message = Message.objects.create(
            room=room, text="hello", contact=self.contact
        )

        with patch.object(Room, "notify_inactivity"):
            room.on_new_message(message, contact=self.contact)

        room.refresh_from_db()
        self.assertFalse(room.is_inactive)

    def test_on_new_message_without_contact_does_not_reset(self):
        """
        If `on_new_message` is somehow called without a contact (defensive
        check), the inactive flag must NOT be cleared.
        """
        room = self._create_inactive_room()
        other_user = User.objects.create(email="other@example.com")
        message = Message.objects.create(room=room, text="hello", user=other_user)

        with patch.object(Room, "notify_inactivity"):
            room.on_new_message(message, contact=None)

        room.refresh_from_db()
        self.assertTrue(room.is_inactive)


class SilentAutomaticMessageTests(TestCase):
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

    def test_creates_message_without_updating_last_interaction(self):
        original_last_interaction = timezone.now() - timedelta(seconds=900)

        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.last_message_user = self.user
        room.last_interaction = original_last_interaction
        room.save()

        with patch.object(Message, "notify_room"):
            message = _send_silent_automatic_message(
                room, "warn me", self.user
            )

        self.assertIsNotNone(message)

        room.refresh_from_db()
        self.assertEqual(
            int(room.last_interaction.timestamp()),
            int(original_last_interaction.timestamp()),
        )
        self.assertEqual(room.last_message_user, self.user)

    def test_returns_none_when_text_is_empty(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        room.user = self.user
        room.save()

        result = _send_silent_automatic_message(room, "", self.user)

        self.assertIsNone(result)
        self.assertFalse(Message.objects.filter(room=room).exists())


class RoomNotifyInactivityTests(TestCase):
    """
    Contract tests for `Room.notify_inactivity`:
    must always emit the dedicated `rooms.inactivity` action with a
    minimal payload `{room_uuid, is_inactive}` to the assigned agent's
    permission group, so the front can update only the inactivity badge
    without re-rendering the whole Room.
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
        self.user = User.objects.create(email="agent@example.com")
        self.contact = Contact.objects.create(name="Contact", external_id="c-1")
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.room.user = self.user
        self.room.save()

    @patch("chats.apps.rooms.models.send_channels_group")
    def test_notify_inactivity_sends_event_with_minimal_payload(self, mock_send):
        permission_mock = MagicMock(pk=42)
        with patch.object(Room, "get_permission", return_value=permission_mock):
            self.room.is_inactive = True
            self.room.notify_inactivity()

        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["action"], "rooms.inactivity")
        self.assertEqual(kwargs["group_name"], "permission_42")
        self.assertEqual(kwargs["call_type"], "notify")
        self.assertEqual(
            kwargs["content"],
            {"room_uuid": str(self.room.uuid), "is_inactive": True},
        )

    @patch("chats.apps.rooms.models.send_channels_group")
    def test_notify_inactivity_emits_false_when_flag_cleared(self, mock_send):
        permission_mock = MagicMock(pk=7)
        with patch.object(Room, "get_permission", return_value=permission_mock):
            self.room.is_inactive = False
            self.room.notify_inactivity()

        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["action"], "rooms.inactivity")
        self.assertEqual(
            kwargs["content"],
            {"room_uuid": str(self.room.uuid), "is_inactive": False},
        )

    @patch("chats.apps.rooms.models.send_channels_group")
    def test_notify_inactivity_does_not_send_when_user_has_no_permission(
        self, mock_send
    ):
        with patch.object(Room, "get_permission", return_value=None):
            self.room.is_inactive = True
            self.room.notify_inactivity()

        mock_send.assert_not_called()
