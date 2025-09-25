import time
import uuid
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.exceptions import (
    MaxPinRoomLimitReachedError,
    RoomIsNotActiveError,
)
from chats.apps.rooms.models import Room
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.sectors.models import Sector


class ConstraintTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def test_unique_contact_queue_is_activetrue_room_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            Room.objects.create(contact=self.room.contact, queue=self.room.queue)
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_contact_queue_is_activetrue_room"'
            in str(context.exception)
        )


@override_settings(ATOMIC_REQUESTS=True)
class TestRoomModel(TransactionTestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )

    def test_user_assigned_at_field(self):
        room = Room.objects.create(queue=self.queue)

        self.assertIsNone(room.user_assigned_at)

        user_a = User.objects.create(email="a@user.com")
        user_b = User.objects.create(email="b@user.com")

        room.user = user_a
        room.save()

        room.refresh_from_db()
        self.assertIsNotNone(room.user_assigned_at)
        self.assertEqual(room.user_assigned_at.date(), timezone.now().date())

        previous_user_assigned_at = room.user_assigned_at

        # changing any other field, user remains the same
        room.project_uuid = uuid.uuid4()
        room.save()

        room.refresh_from_db()
        self.assertEqual(room.user_assigned_at, previous_user_assigned_at)

        room.user = user_b
        room.save()

        room.refresh_from_db()
        self.assertNotEqual(room.user_assigned_at, previous_user_assigned_at)

    def test_pin_room(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)

        self.assertEqual(room.pins.count(), 0)

        room.pin(user)
        self.assertEqual(room.pins.count(), 1)

        pin = room.pins.first()
        self.assertEqual(pin.user, user)

        room.pin(user)
        # Should not raise an error or add a new pin
        self.assertEqual(room.pins.count(), 1)
        self.assertEqual(room.pins.first(), pin)

        queue_2 = Queue.objects.create(
            sector=Sector.objects.create(
                project=Project.objects.create(),
                rooms_limit=10,
                work_start="09:00",
                work_end="18:00",
            ),
        )

        for i in range(settings.MAX_ROOM_PINS_LIMIT):
            room = Room.objects.create(
                user=user,
                queue=queue_2,
            )
            room.pin(user)

        room = Room.objects.create(user=user, queue=self.queue)

        # Should not raise an error because the limit is not reached
        # since the previous rooms are from a different project
        room.pin(user)

    def test_pin_room_limit_reached(self):
        user = User.objects.create(email="a@user.com")

        for i in range(settings.MAX_ROOM_PINS_LIMIT):
            room = Room.objects.create(user=user, queue=self.queue)

            room.pin(user)

        room = Room.objects.create(queue=self.queue)

        with self.assertRaises(MaxPinRoomLimitReachedError):
            room.pin(user)

    def test_pin_room_user_not_assigned(self):
        room = Room.objects.create(queue=self.queue)
        user = User.objects.create(email="a@user.com")

        with self.assertRaises(PermissionDenied):
            room.pin(user)

    def test_pin_room_is_not_active(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)
        room.close()

        with self.assertRaises(RoomIsNotActiveError):
            room.pin(user)

    def test_unpin_room(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)

        room.pin(user)
        self.assertEqual(room.pins.count(), 1)

        pin = room.pins.first()
        self.assertEqual(pin.user, user)

        room.unpin(user)
        self.assertEqual(room.pins.count(), 0)

    def test_unpin_room_user_not_assigned(self):
        room = Room.objects.create(queue=self.queue)
        user = User.objects.create(email="a@user.com")

        with self.assertRaises(PermissionDenied):
            room.unpin(user)

    def test_clear_pins(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)

        room.pin(user)
        self.assertEqual(room.pins.count(), 1)

        room.clear_pins()
        self.assertEqual(room.pins.count(), 0)

    def test_change_user_clears_pins(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)

        room.pin(user)
        self.assertEqual(room.pins.count(), 1)

        room.user = User.objects.create(email="b@user.com")
        room.save()

        self.assertEqual(room.pins.count(), 0)

    def test_remove_user_clears_pins(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)

        room.pin(user)
        self.assertEqual(room.pins.count(), 1)

        room.user = None
        room.save()

        self.assertEqual(room.pins.count(), 0)

    def test_close_room_clears_pins(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(user=user, queue=self.queue)

        room.pin(user)
        self.assertEqual(room.pins.count(), 1)

        room.close()
        self.assertEqual(room.pins.count(), 0)

    def test_add_to_queue_at_field(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(queue=self.queue)

        added_to_queue_at = room.added_to_queue_at

        self.assertEqual(
            added_to_queue_at.strftime("%Y-%m-%d %H:%M:%S"),
            room.created_on.strftime("%Y-%m-%d %H:%M:%S"),
        )

        time.sleep(1)

        room.user = user
        room.save()

        room.refresh_from_db()

        # added_to_queue_at should not change
        self.assertEqual(room.added_to_queue_at, added_to_queue_at)

        time.sleep(1)

        room.user = None
        room.save()

        room.refresh_from_db()

        # added_to_queue_at should change when user is removed
        # as, in practice, the room is added to the queue
        self.assertNotEqual(room.added_to_queue_at, added_to_queue_at)

    def test_add_transfer_to_history(self):
        user = User.objects.create(email="a@user.com")
        room = Room.objects.create(queue=self.queue)
        self.assertEqual(room.full_transfer_history, [])
        feedback = create_transfer_json(
            action="transfer",
            from_=room.queue,
            to=user,
        )
        room.add_transfer_to_history(feedback)
        self.assertEqual(room.full_transfer_history, [feedback])
        self.assertEqual(room.transfer_history, feedback)

        other_feedback = create_transfer_json(
            action="transfer",
            from_=room.queue,
            to=user,
        )
        room.add_transfer_to_history(other_feedback)
        self.assertEqual(room.full_transfer_history, [feedback, other_feedback])
        self.assertEqual(room.transfer_history, other_feedback)

    @patch("chats.apps.sectors.tasks.send_automatic_message.apply_async")
    def test_send_automatic_message_when_room_is_created_with_user(
        self, mock_send_automatic_message
    ):
        mock_send_automatic_message.return_value = None

        user = User.objects.create(email="a@user.com")

        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = "Test Message"
        self.sector.save()

        room = Room.objects.create(user=user, queue=self.queue)

        room.send_automatic_message()

        mock_send_automatic_message.assert_called_once_with(
            args=[room.uuid, self.sector.automatic_message_text, user.id],
            countdown=0,
        )

    @patch("chats.apps.sectors.tasks.send_automatic_message.apply_async")
    def test_send_automatic_message_when_room_is_updated_with_user(
        self, mock_send_automatic_message
    ):
        mock_send_automatic_message.return_value = None

        user = User.objects.create(email="a@user.com")

        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = "Test Message"
        self.sector.save()

        room = Room.objects.create(queue=self.queue)

        mock_send_automatic_message.assert_not_called()

        room.user = user
        room.save()

        room.send_automatic_message()

        mock_send_automatic_message.assert_called_once_with(
            args=[room.uuid, self.sector.automatic_message_text, user.id],
            countdown=0,
        )

    @patch("chats.apps.sectors.tasks.send_automatic_message.apply_async")
    def test_do_not_send_automatic_message_when_sector_automatic_message_is_not_active(
        self, mock_send_automatic_message
    ):
        mock_send_automatic_message.return_value = None
        user = User.objects.create(email="a@user.com")

        self.sector.is_automatic_message_active = False
        self.sector.save()

        room = Room.objects.create(user=user, queue=self.queue)

        room.send_automatic_message()

        mock_send_automatic_message.assert_not_called()
