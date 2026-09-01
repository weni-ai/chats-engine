import uuid

from django.test import TestCase

from chats.apps.projects.models import Project, TemplateType
from chats.apps.projects.usecases.exceptions import InvalidTemplateTypeData
from chats.apps.projects.usecases.template_type_creation import TemplateTypeCreation
from chats.apps.sectors.models import Sector


class TestTemplateTypeCreation(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="TT Test Project")
        self.template_uuid = str(uuid.uuid4())

    def test_create_raises_when_project_not_found(self):
        config = {"project_uuid": str(uuid.uuid4()), "uuid": self.template_uuid, "name": "x"}
        with self.assertRaises(InvalidTemplateTypeData):
            TemplateTypeCreation(config=config).create()

    def test_create_creates_template_with_setup_from_active_sectors(self):
        sector_a = Sector.objects.create(
            name="Sector A",
            project=self.project,
            rooms_limit=3,
            work_start="08:00",
            work_end="18:00",
        )
        sector_b = Sector.objects.create(
            name="Sector B",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="17:00",
        )

        config = {
            "project_uuid": str(self.project.uuid),
            "uuid": self.template_uuid,
            "name": "My Template",
        }
        template_type = TemplateTypeCreation(config=config).create()

        self.assertEqual(template_type.name, "My Template")
        self.assertEqual(str(template_type.uuid), self.template_uuid)
        sector_names = {s["name"] for s in template_type.setup["sectors"]}
        self.assertEqual(sector_names, {sector_a.name, sector_b.name})

    def test_create_excludes_deleted_sectors(self):
        Sector.objects.create(
            name="Active Sector",
            project=self.project,
            rooms_limit=3,
            work_start="08:00",
            work_end="18:00",
        )
        Sector.objects.create(
            name="Deleted Sector",
            project=self.project,
            rooms_limit=3,
            work_start="08:00",
            work_end="18:00",
            is_deleted=True,
        )

        config = {
            "project_uuid": str(self.project.uuid),
            "uuid": self.template_uuid,
            "name": "Filtered Template",
        }
        template_type = TemplateTypeCreation(config=config).create()

        sector_names = [s["name"] for s in template_type.setup["sectors"]]
        self.assertEqual(sector_names, ["Active Sector"])

    def test_create_updates_existing_template_type(self):
        TemplateType.objects.create(uuid=self.template_uuid, name="Old", setup={})

        config = {
            "project_uuid": str(self.project.uuid),
            "uuid": self.template_uuid,
            "name": "New Name",
        }
        template_type = TemplateTypeCreation(config=config).create()

        self.assertEqual(template_type.name, "New Name")
        self.assertEqual(TemplateType.objects.filter(uuid=self.template_uuid).count(), 1)
