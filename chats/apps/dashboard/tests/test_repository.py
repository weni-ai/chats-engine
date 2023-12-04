from operator import attrgetter
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.serializers import (
    dashboard_general_data,
)
from chats.apps.projects.models import Project

from chats.apps.api.v1.dashboard.repository import AgentRepository
from chats.apps.api.v1.dashboard.dto import Filters


class RepositoryTests(TestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.user = User.objects.get(pk="8")

    def test_returned_fields_from_get_agents_data(self):
        project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")

        instance = AgentRepository()
        filter = Filters(is_weni_admin=True)
        agents_fields = instance.get_agents_data(
            filters=filter,
            project=project,
        )
        for fields in agents_fields:
            self.assertTrue(hasattr(fields, "first_name"))
            self.assertTrue(hasattr(fields, "email"))
            self.assertTrue(hasattr(fields, "agent_status"))
            self.assertTrue(hasattr(fields, "closed_rooms"))
            self.assertTrue(hasattr(fields, "opened_rooms"))

    def test_field_value_from_dashboard_agent_serializer(self):
        project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")
        instance = AgentRepository()
        filter = Filters(is_weni_admin=True)
        agents_fields = instance.get_agents_data(
            filters=filter,
            project=project,
        )

        self.assertEqual(agents_fields[2].first_name, "")
        self.assertEqual(agents_fields[2].email, "amywong@chats.weni.ai")
        self.assertEqual(agents_fields[2].agent_status, "OFFLINE")
        self.assertEqual(agents_fields[2].closed_rooms, 0)
        self.assertEqual(agents_fields[2].opened_rooms, 1)
