from typing import Any, Dict

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.serializers import DashboardAgentsSerializer
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
        self.user = User.objects.get(pk="8")

    def test_returned_fields_from_dashboard_agent_serializer(self):
        serializer_data: Dict[str, Any] = {
            "first_name": "John",
            "email": "invalid_email",
            "agent_status": "ACTIVE",
            "closed_rooms": 3,
            "opened_rooms": 5,
        }
        serializer = DashboardAgentsSerializer(data=serializer_data)
        self.assertFalse(serializer.is_valid())

        serializer_data["email"] = "john@example.com"
        serializer_data["first_name"] = {}
        serializer = DashboardAgentsSerializer(data=serializer_data)
        self.assertFalse(serializer.is_valid())
