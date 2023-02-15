from django.db import IntegrityError
from rest_framework.test import APITestCase

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
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
