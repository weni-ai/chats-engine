from django.db import IntegrityError
from rest_framework.test import APITestCase

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization


class ConstraintTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
       self.project_permission = ProjectPermission.objects.get(uuid="e416fd45-2896-43a5-bd7a-5067f03c77fa")
       self.queue = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")
       self.queue_auth = QueueAuthorization.objects.get(uuid="3717f056-7ea5-4d38-80f5-ba907132807c")

    def test_unique_user_permission_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            project_permission = ProjectPermission.objects.create(
                user=self.project_permission.user, project=self.project_permission.project
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_user_permission"' in str(context.exception))

    def test_unique_queue_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            queue = Queue.objects.create(
                name=self.queue.name, sector=self.queue.sector
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_queue_name"' in str(context.exception))

    def test_unique_queue_auth_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            queue_auth = QueueAuthorization.objects.create(
                queue=self.queue_auth.queue, permission=self.queue_auth.permission
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_queue_auth"' in str(context.exception))