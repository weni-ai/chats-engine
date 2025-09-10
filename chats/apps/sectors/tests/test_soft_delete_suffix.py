from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue


class QueueSoftDeleteSuffixTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email="deleter@example.com", password="x"
        )
        self.project = Project.objects.create(name="P1")
        self.sector = Sector.objects.create(
            name="S1", project=self.project, rooms_limit=5
        )

    def test_queue_delete_includes_user_email_in_suffix(self):
        q = Queue.objects.create(name="Q1", sector=self.sector)
        q.delete(user=self.user)
        q.refresh_from_db()
        self.assertTrue(q.is_deleted)
        self.assertIn("_is_deleted_", q.name)
        self.assertIn(self.user.email, q.name)

    def test_queue_delete_uses_system_in_suffix_when_user_absent(self):
        q = Queue.objects.create(name="Q2", sector=self.sector)
        q.delete()
        q.refresh_from_db()
        self.assertTrue(q.is_deleted)
        self.assertIn("_is_deleted_", q.name)
        self.assertIn("system", q.name)
