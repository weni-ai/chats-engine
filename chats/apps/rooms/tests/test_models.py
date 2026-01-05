import time
import uuid
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from django.utils.timezone import timedelta
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.exceptions import (
    MaxPinRoomLimitReachedError,
    RoomIsNotActiveError,
)
from chats.apps.rooms.models import Room
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.sectors.models import Sector, SectorTag


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
            args=[room.uuid, self.sector.automatic_message_text, user.id, False],
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
            args=[room.uuid, self.sector.automatic_message_text, user.id, False],
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

    def test_change_queue_without_changing_sector(self):
        other_queue = Queue.objects.create(sector=self.sector, name="Other Queue")
        tags = SectorTag.objects.create(sector=self.sector, name="Test Tag")

        room = Room.objects.create(queue=self.queue)
        room.tags.add(tags)
        self.assertEqual(room.tags.count(), 1)

        room.queue = other_queue
        room.save()

        self.assertEqual(room.tags.count(), 1)

    def test_change_queue_changing_sector(self):
        other_queue = Queue.objects.create(
            sector=Sector.objects.create(
                project=self.project,
                name="Other Sector",
                rooms_limit=10,
                work_start="09:00",
                work_end="18:00",
            ),
            name="Other Queue",
        )
        tags = SectorTag.objects.create(sector=self.sector, name="Test Tag")

        room = Room.objects.create(queue=self.queue)
        room.tags.add(tags)
        self.assertEqual(room.tags.count(), 1)

        room.queue = other_queue
        room.save()

        self.assertEqual(room.tags.count(), 0)

    @patch("chats.apps.rooms.models.Room.get_24h_valid_from_cache")
    @patch("chats.apps.rooms.models.Room.save_24h_valid_to_cache")
    def test_room_24h_valid_when_room_urn_is_not_whatsapp(
        self, save_24h_valid_to_cache, get_24h_valid_from_cache
    ):
        room = Room.objects.create(queue=self.queue, urn="test")
        self.assertTrue(room.is_24h_valid)

        get_24h_valid_from_cache.assert_not_called()
        save_24h_valid_to_cache.assert_not_called()

    @patch("chats.apps.rooms.models.Room.get_24h_valid_from_cache")
    @patch("chats.apps.rooms.models.Room.save_24h_valid_to_cache")
    def test_room_24h_valid_when_room_response_is_cached(
        self, save_24h_valid_to_cache, get_24h_valid_from_cache
    ):
        get_24h_valid_from_cache.return_value = True
        room = Room.objects.create(queue=self.queue, urn="whatsapp:1234567890")
        self.assertTrue(room.is_24h_valid)

        get_24h_valid_from_cache.assert_called_once()
        save_24h_valid_to_cache.assert_not_called()

    @patch("chats.apps.rooms.models.Room.get_24h_valid_from_cache")
    @patch("chats.apps.rooms.models.Room.save_24h_valid_to_cache")
    def test_room_24h_valid_when_room_contact_messages_are_in_24_hour_window(
        self, save_24h_valid_to_cache, get_24h_valid_from_cache
    ):
        get_24h_valid_from_cache.return_value = None
        room = Room.objects.create(queue=self.queue, urn="whatsapp:1234567890")
        Message.objects.create(room=room, contact=room.contact, text="Test Message")
        self.assertTrue(room.is_24h_valid)

        get_24h_valid_from_cache.assert_called()
        save_24h_valid_to_cache.assert_called()

    @patch("chats.apps.rooms.models.Room.get_24h_valid_from_cache")
    @patch("chats.apps.rooms.models.Room.save_24h_valid_to_cache")
    def test_room_24h_valid_when_room_contact_messages_are_not_in_24_hour_window(
        self, save_24h_valid_to_cache, get_24h_valid_from_cache
    ):
        get_24h_valid_from_cache.return_value = None

        now = timezone.now()
        yesterday = now - timedelta(days=1, hours=1)

        with patch("chats.apps.rooms.models.timezone.now") as mock_now:
            mock_now.return_value = yesterday
            room = Room.objects.create(queue=self.queue, urn="whatsapp:1234567890")
            Message.objects.create(
                room=room,
                contact=room.contact,
                text="Test Message",
                created_on=yesterday,
            )

        self.assertFalse(room.is_24h_valid)

        get_24h_valid_from_cache.assert_called()
        save_24h_valid_to_cache.assert_called()

    @patch("chats.apps.rooms.models.cache")
    @patch("chats.apps.rooms.models.ROOM_24H_VALID_CACHE_TTL")
    def test_get_24h_valid_from_cache(self, mock_room_24h_valid_cache_ttl, mock_cache):
        mock_room_24h_valid_cache_ttl.return_value = 30
        mock_cache.get.return_value = True
        room = Room.objects.create(queue=self.queue, urn="whatsapp:1234567890")
        self.assertTrue(room.get_24h_valid_from_cache())

        mock_cache.get.assert_called_once_with(room.room_24h_valid_cache_key)

    @patch("chats.apps.rooms.models.cache")
    @patch("chats.apps.rooms.models.ROOM_24H_VALID_CACHE_TTL")
    def test_save_24h_valid_to_cache(self, mock_room_24h_valid_cache_ttl, mock_cache):
        mock_room_24h_valid_cache_ttl.return_value = 30
        mock_cache.set.return_value = True
        room = Room.objects.create(queue=self.queue, urn="whatsapp:1234567890")
        room.save_24h_valid_to_cache(True)
        mock_cache.set.assert_called()


class TestHandleRoomCloseTags(TransactionTestCase):
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
        self.room = Room.objects.create(queue=self.queue)
        self.tags = [
            SectorTag.objects.create(name="Test Tag 1", sector=self.sector),
        ]
        self.room.tags.add(self.tags[0])

    def test_handle_close_tags_adding_a_new_tag_and_keeping_the_current(self):
        close_tags = [
            self.tags[0].uuid,
            SectorTag.objects.create(name="Test Tag 2", sector=self.sector).uuid,
        ]

        self.assertEqual(
            list(self.room.tags.values_list("uuid", flat=True)), [self.tags[0].uuid]
        )
        self.room._handle_close_tags(close_tags)

        self.assertEqual(
            list(self.room.tags.values_list("uuid", flat=True)), close_tags
        )

    def test_handle_close_tags_removing_the_current(self):
        close_tags = []

        self.assertEqual(
            list(self.room.tags.values_list("uuid", flat=True)), [self.tags[0].uuid]
        )
        self.room._handle_close_tags(close_tags)

        self.assertEqual(
            list(self.room.tags.values_list("uuid", flat=True)), close_tags
        )

    def test_handle_close_tags_replacing_the_current(self):
        close_tags = [
            self.tags[0].uuid,
        ]

        self.assertEqual(
            list(self.room.tags.values_list("uuid", flat=True)), [self.tags[0].uuid]
        )
        self.room._handle_close_tags(close_tags)

        self.assertEqual(
            list(self.room.tags.values_list("uuid", flat=True)), close_tags
        )


class TestRoomUnreadMessagesCount(TransactionTestCase):
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
        self.room = Room.objects.create(queue=self.queue)

    def test_increment_unread_messages_count(self):
        self.assertIsNone(self.room.last_unread_message_at)
        self.assertEqual(self.room.unread_messages_count, 0)

        self.room.increment_unread_messages_count(1, timezone.now())
        self.room.refresh_from_db()
        self.assertEqual(self.room.unread_messages_count, 1)
        self.assertIsNone(self.room.last_unread_message_at)

        self.room.increment_unread_messages_count(2, timezone.now())
        self.room.refresh_from_db()
        self.assertEqual(self.room.unread_messages_count, 3)
        self.assertIsNone(self.room.last_unread_message_at)

    def test_clear_unread_messages_count(self):
        self.room.increment_unread_messages_count(1, timezone.now())
        self.room.refresh_from_db()
        self.assertEqual(self.room.unread_messages_count, 1)
        self.assertIsNone(self.room.last_unread_message_at)

        self.room.clear_unread_messages_count()
        self.room.refresh_from_db()
        self.assertEqual(self.room.unread_messages_count, 0)
        self.assertIsNotNone(self.room.last_unread_message_at)


class TestUpdateLastMessage(APITestCase):
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
        self.room = Room.objects.create(queue=self.queue)

    def test_update_last_message(self):
        self.assertIsNone(self.room.last_interaction)
        self.assertIsNone(self.room.last_message_uuid)
        self.assertEqual(self.room.last_message_text, "")

        msg_uuid = uuid.uuid4()
        now = timezone.now()

        self.room.update_last_message(
            message_uuid=msg_uuid,
            text="Hello world",
            created_on=now,
        )
        self.room.refresh_from_db()

        self.assertEqual(self.room.last_interaction, now)
        self.assertEqual(self.room.last_message_uuid, msg_uuid)
        self.assertEqual(self.room.last_message_text, "Hello world")

    def test_update_last_message_overwrites_previous(self):
        msg_uuid_1 = uuid.uuid4()
        now_1 = timezone.now()

        self.room.update_last_message(
            message_uuid=msg_uuid_1,
            text="First message",
            created_on=now_1,
        )
        self.room.refresh_from_db()
        self.assertEqual(self.room.last_message_text, "First message")

        msg_uuid_2 = uuid.uuid4()
        now_2 = timezone.now()

        self.room.update_last_message(
            message_uuid=msg_uuid_2,
            text="Second message",
            created_on=now_2,
        )
        self.room.refresh_from_db()

        self.assertEqual(self.room.last_message_uuid, msg_uuid_2)
        self.assertEqual(self.room.last_message_text, "Second message")
        self.assertEqual(self.room.last_interaction, now_2)


class TestOnNewMessage(APITestCase):
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
        self.room = Room.objects.create(queue=self.queue)

    def test_on_new_message_updates_all_fields(self):
        self.assertIsNone(self.room.last_interaction)
        self.assertIsNone(self.room.last_contact_interaction)
        self.assertIsNone(self.room.last_message_uuid)

        msg_uuid = uuid.uuid4()
        now = timezone.now()

        self.room.on_new_message(
            message_uuid=msg_uuid,
            text="Contact message",
            created_on=now,
        )
        self.room.refresh_from_db()

        self.assertEqual(self.room.last_interaction, now)
        self.assertEqual(self.room.last_contact_interaction, now)
        self.assertEqual(self.room.last_message_uuid, msg_uuid)
        self.assertEqual(self.room.last_message_text, "Contact message")

    def test_on_new_message_increments_unread(self):
        self.assertEqual(self.room.unread_messages_count, 0)

        msg_uuid = uuid.uuid4()
        now = timezone.now()

        self.room.on_new_message(
            message_uuid=msg_uuid,
            text="Message 1",
            created_on=now,
            increment_unread=1,
        )
        self.room.refresh_from_db()
        self.assertEqual(self.room.unread_messages_count, 1)

        msg_uuid_2 = uuid.uuid4()
        now_2 = timezone.now()

        self.room.on_new_message(
            message_uuid=msg_uuid_2,
            text="Message 2",
            created_on=now_2,
            increment_unread=3,
        )
        self.room.refresh_from_db()
        self.assertEqual(self.room.unread_messages_count, 4)

    def test_on_new_message_only_updates_if_newer(self):
        msg_uuid_1 = uuid.uuid4()
        now = timezone.now()

        self.room.on_new_message(
            message_uuid=msg_uuid_1,
            text="Recent message",
            created_on=now,
        )
        self.room.refresh_from_db()
        self.assertEqual(self.room.last_message_text, "Recent message")

        msg_uuid_2 = uuid.uuid4()
        old_time = now - timedelta(hours=1)

        self.room.on_new_message(
            message_uuid=msg_uuid_2,
            text="Old message",
            created_on=old_time,
        )
        self.room.refresh_from_db()

        self.assertEqual(self.room.last_message_text, "Recent message")
        self.assertEqual(self.room.last_message_uuid, msg_uuid_1)
        self.assertEqual(self.room.last_interaction, now)

    def test_on_new_message_without_increment_unread(self):
        self.assertEqual(self.room.unread_messages_count, 0)

        msg_uuid = uuid.uuid4()
        now = timezone.now()

        self.room.on_new_message(
            message_uuid=msg_uuid,
            text="Message without unread",
            created_on=now,
            increment_unread=0,
        )
        self.room.refresh_from_db()

        self.assertEqual(self.room.unread_messages_count, 0)
        self.assertEqual(self.room.last_message_text, "Message without unread")
