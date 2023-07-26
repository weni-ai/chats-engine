from django.test import TestCase

from chats.apps.api.v1.dashboard.serializers import (
    dashboard_general_data,
    dashboard_agents_data,
)

from chats.apps.projects.models import Project


class RedisMock:
    cache = {}

    def set(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache[key]


class SerializerTests(TestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")

    def test_active_chats_function_passing_sector(self):
        serializer = dashboard_general_data(
            context={"sector": "d49049f0-c601-4e05-a293-98c1dea5fe4f"},
            project=self.project,
        )
        self.assertEqual(serializer["active_chats"], 0)

    def test_active_chats_function_without_filter(self):
        serializer = dashboard_general_data(
            context={},
            project=self.project,
        )
        self.assertEqual(serializer["active_chats"], 1)

    def test_returned_fields_from_dashboard_agent_serializer(self):
        project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")
        instance = dashboard_agents_data(
            project=project,
            context={"is_weni_admin": True},
        )
        self.assertEqual(list(instance[0].keys())[0], "first_name")
        self.assertEqual(list(instance[0].keys())[1], "email")
        self.assertEqual(list(instance[0].keys())[2], "agent_status")
        self.assertEqual(list(instance[0].keys())[3], "closed_rooms")
        self.assertEqual(list(instance[0].keys())[4], "opened_rooms")

    def test_field_value_from_dashboard_agent_serializer(self):
        project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")
        instance = dashboard_agents_data(
            project=project,
            context={"is_weni_admin": True},
        )

        self.assertEqual(instance[0]["first_name"], "")
        self.assertEqual(instance[0]["email"], "amywong@chats.weni.ai")
        self.assertEqual(instance[0]["agent_status"], "OFFLINE")
        self.assertEqual(instance[0]["closed_rooms"], 0)
        self.assertEqual(instance[0]["opened_rooms"], 1)
        
    def test_returned_fields_from_dashboard_agent_serializer(self):
        project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")
        instance = dashboard_agents_data(
            project=project,
            context={"is_weni_admin": True},
        )
        self.assertEqual(list(instance[0].keys())[0], "first_name")
        self.assertEqual(list(instance[0].keys())[1], "email")
        self.assertEqual(list(instance[0].keys())[2], "agent_status")
        self.assertEqual(list(instance[0].keys())[3], "closed_rooms")
        self.assertEqual(list(instance[0].keys())[4], "opened_rooms")

    def test_field_value_from_dashboard_agent_serializer(self):
        project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")
        instance = dashboard_agents_data(
            project=project,
            context={"is_weni_admin": True},
        )

        self.assertEqual(instance[2]["first_name"], "")
        self.assertEqual(instance[2]["email"], "amywong@chats.weni.ai")
        self.assertEqual(instance[2]["agent_status"], "OFFLINE")
        self.assertEqual(instance[2]["closed_rooms"], 0)
        self.assertEqual(instance[2]["opened_rooms"], 1)
