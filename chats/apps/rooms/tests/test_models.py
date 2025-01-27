import uuid
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.rooms.models import Room


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


class TestRoomModel(TestCase):
    def test_user_assigned_at_field(self):
        room = Room.objects.create()

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
