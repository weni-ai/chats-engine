import uuid
from unittest.mock import MagicMock

from django.test import TestCase

from chats.apps.api.v1.orgs.serializers import OrgProjectSerializer
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


class TestOrgProjectSerializerItsPrincipal(TestCase):
    def _make_obj(self, config):
        obj = MagicMock()
        obj.config = config
        obj.uuid = uuid.uuid4()
        return obj

    def test_returns_value_from_config_dict(self):
        serializer = OrgProjectSerializer()
        obj = self._make_obj({"its_principal": True})
        self.assertTrue(serializer.get_its_principal(obj))

    def test_returns_false_when_key_missing_in_config(self):
        serializer = OrgProjectSerializer()
        obj = self._make_obj({})
        self.assertFalse(serializer.get_its_principal(obj))

    def test_returns_none_when_config_is_none(self):
        serializer = OrgProjectSerializer()
        obj = self._make_obj(None)
        self.assertIsNone(serializer.get_its_principal(obj))


class TestOrgProjectSerializerHasSectorIntegration(TestCase):
    def test_returns_false_when_no_sector_links_to_project_as_secondary(self):
        project = Project.objects.create(name="No Integ Project")
        serializer = OrgProjectSerializer()
        self.assertFalse(serializer.get_has_sector_integration(project))

    def test_returns_true_when_a_sector_links_to_project_as_secondary(self):
        principal = Project.objects.create(name="Principal")
        secondary = Project.objects.create(name="Secondary")
        Sector.objects.create(
            name="Linked Sector",
            project=principal,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
            secondary_project={"uuid": str(secondary.uuid)},
        )

        serializer = OrgProjectSerializer()
        self.assertTrue(serializer.get_has_sector_integration(secondary))
