from django.db import IntegrityError
from rest_framework.test import APITestCase

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class ConstraintTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project_permission = ProjectPermission.objects.get(
            uuid="e416fd45-2896-43a5-bd7a-5067f03c77fa"
        )

    def test_unique_user_permission_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            ProjectPermission.objects.create(
                user=self.project_permission.user,
                project=self.project_permission.project,
            )
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_user_permission"'
            in str(context.exception)
        )
