from django.test import TestCase

from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class QueueManagerTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=100,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def test_get_queryset_with_include_deleted(self):
        self.assertIn(self.queue, Queue.objects.all())
        self.assertIn(self.queue, Queue.all_objects.all())

        self.queue.delete()

        self.assertNotIn(self.queue, Queue.objects.all())
        self.assertIn(self.queue, Queue.all_objects.all())
