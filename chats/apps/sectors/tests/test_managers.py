from django.test import TestCase

from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector


class SectorManagerTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=100,
            work_start="08:00",
            work_end="18:00",
        )

    def test_get_queryset_with_include_deleted(self):
        self.assertIn(self.sector, Sector.objects.all())
        self.assertIn(self.sector, Sector.all_objects.all())

        self.sector.delete()

        self.assertNotIn(self.sector, Sector.objects.all())
        self.assertIn(self.sector, Sector.all_objects.all())
